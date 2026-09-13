import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class ParquetExporter:
    """
    Serializes normalized UES events into timestamp-partitioned Apache Parquet datasets.
    Guarantees field preservation, traceability, and schema-safe custom fields.
    """

    @staticmethod
    def write_partitioned_parquet(
        records: List[Dict[str, Any]],
        base_dir: str
    ) -> Tuple[int, int, List[str], int]:
        """
        Writes a batch of normalized records to partitioned Parquet files.

        Returns:
            Tuple[files_created, bytes_written, file_paths, partition_count]
        """
        if not records:
            return 0, 0, [], 0

        # 1. Clean and serialize nested structures for Parquet compatibility
        cleaned_records = []
        for r in records:
            item = dict(r)
            # Serialize dict/list fields to JSON strings to maintain schema compatibility
            if isinstance(item.get("custom_fields"), (dict, list)):
                item["custom_fields"] = json.dumps(item["custom_fields"])
            elif item.get("custom_fields") is None:
                item["custom_fields"] = None

            if isinstance(item.get("tags"), list):
                item["tags"] = json.dumps(item["tags"])
            elif item.get("tags") is None:
                item["tags"] = None

            cleaned_records.append(item)

        df = pd.DataFrame(cleaned_records)

        # 2. Extract partition keys from timestamp (or ingestion_timestamp fallback)
        ts_series = pd.to_datetime(df.get("timestamp"), errors="coerce", utc=True)
        fallback_ts = pd.to_datetime(df.get("ingestion_timestamp"), errors="coerce", utc=True)
        ts_series = ts_series.fillna(fallback_ts)
        now_dt = datetime.now(timezone.utc)

        df["_year"] = ts_series.dt.strftime("%Y").fillna(now_dt.strftime("%Y"))
        df["_month"] = ts_series.dt.strftime("%m").fillna(now_dt.strftime("%m"))
        df["_day"] = ts_series.dt.strftime("%d").fillna(now_dt.strftime("%d"))

        files_created = 0
        bytes_written = 0
        file_paths = []
        partitions_set = set()

        # 3. Group by (year, month, day) partition and write Parquet files
        for (year, month, day), group in df.groupby(["_year", "_month", "_day"]):
            partition_key = f"year={year}/month={month}/day={day}"
            partitions_set.add(partition_key)

            partition_dir = os.path.join(base_dir, f"year={year}", f"month={month}", f"day={day}")
            os.makedirs(partition_dir, exist_ok=True)

            # Drop temporary partition helper columns before writing
            write_df = group.drop(columns=["_year", "_month", "_day"])

            filename = f"events-{uuid.uuid4().hex[:12]}.parquet"
            filepath = os.path.join(partition_dir, filename)

            # Convert to PyArrow Table and write with snappy compression
            table = pa.Table.from_pandas(write_df, preserve_index=False)
            pq.write_table(table, filepath, compression="snappy")

            file_size = os.path.getsize(filepath)
            bytes_written += file_size
            files_created += 1
            file_paths.append(os.path.abspath(filepath))

        return files_created, bytes_written, file_paths, len(partitions_set)
