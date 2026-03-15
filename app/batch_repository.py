from typing import List, Dict, Any, Optional
from datetime import datetime

from app.database import execute_query, execute_update, execute_single_query


def insert_batch_job_log(
    job_name: str,
    run_type: str,
    started_at: datetime,
    status: str = "RUNNING",
    message: str = None,
    total_count: int = None,
    success_count: int = None,
    fail_count: int = None
) -> int:
    """배치 작업 로그 추가"""
    query = """
    INSERT INTO batch_job_log (
        job_name, run_type, started_at, finished_at, status, message,
        total_count, success_count, fail_count, created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    RETURNING id
    """
    return execute_update(
        query,
        (job_name, run_type, started_at, None, status, message, total_count, success_count, fail_count)
    )


def update_batch_job_log(
    job_id: int,
    finished_at: datetime,
    status: str,
    message: str = None,
    total_count: int = None,
    success_count: int = None,
    fail_count: int = None
) -> int:
    """배치 작업 로그 업데이트"""
    query = """
    UPDATE batch_job_log
    SET finished_at = %s, status = %s, message = %s,
        total_count = %s, success_count = %s, fail_count = %s
    WHERE id = %s
    """
    return execute_update(
        query,
        (finished_at, status, message, total_count, success_count, fail_count, job_id)
    )


def get_batch_job_logs_by_job(job_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """작업명별 배치 로그 조회"""
    query = """
    SELECT id, job_name, run_type, started_at, finished_at, status, message,
           total_count, success_count, fail_count, created_at
    FROM batch_job_log
    WHERE job_name = %s
    ORDER BY started_at DESC
    LIMIT %s
    """
    return execute_query(query, (job_name, limit))


def get_latest_batch_job_log(job_name: str) -> Optional[Dict[str, Any]]:
    """가장 최신 배치 작업 로그 조회"""
    query = """
    SELECT id, job_name, run_type, started_at, finished_at, status, message,
           total_count, success_count, fail_count, created_at
    FROM batch_job_log
    WHERE job_name = %s
    ORDER BY started_at DESC
    LIMIT 1
    """
    return execute_single_query(query, (job_name,))


def get_running_batch_jobs() -> List[Dict[str, Any]]:
    """실행 중인 배치 작업 조회"""
    query = """
    SELECT id, job_name, run_type, started_at, finished_at, status, message,
           total_count, success_count, fail_count, created_at
    FROM batch_job_log
    WHERE status = 'RUNNING'
    ORDER BY started_at DESC
    """
    return execute_query(query)


def get_batch_job_logs_by_date_range(
    start_date: datetime,
    end_date: datetime,
    job_name: str = None
) -> List[Dict[str, Any]]:
    """날짜 범위별 배치 로그 조회"""
    if job_name:
        query = """
        SELECT id, job_name, run_type, started_at, finished_at, status, message,
               total_count, success_count, fail_count, created_at
        FROM batch_job_log
        WHERE started_at >= %s AND started_at <= %s AND job_name = %s
        ORDER BY started_at DESC
        """
        return execute_query(query, (start_date, end_date, job_name))
    else:
        query = """
        SELECT id, job_name, run_type, started_at, finished_at, status, message,
               total_count, success_count, fail_count, created_at
        FROM batch_job_log
        WHERE started_at >= %s AND started_at <= %s
        ORDER BY started_at DESC
        """
        return execute_query(query, (start_date, end_date))


def get_batch_job_statistics(days: int = 7) -> List[Dict[str, Any]]:
    """배치 작업 통계 조회"""
    query = """
    SELECT 
        job_name,
        COUNT(*) as total_runs,
        COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count,
        COUNT(CASE WHEN status = 'RUNNING' THEN 1 END) as running_count,
        AVG(EXTRACT(EPOCH FROM (finished_at - started_at))) as avg_duration_seconds
    FROM batch_job_log
    WHERE started_at >= NOW() - INTERVAL '%s days'
    GROUP BY job_name
    ORDER BY job_name
    """
    return execute_query(query, (days,))


def cleanup_old_batch_logs(keep_days: int = 30) -> int:
    """오래된 배치 로그 정리"""
    query = """
    DELETE FROM batch_job_log
    WHERE created_at < NOW() - INTERVAL '%s days'
    """
    return execute_update(query, (keep_days,))
