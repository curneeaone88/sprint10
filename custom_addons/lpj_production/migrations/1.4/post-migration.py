# -*- coding: utf-8 -*-
def migrate(cr, version):
    """OK yang sudah Done sebelum field date_done ada: pakai write_date sebagai
    perkiraan tanggal selesai, lalu hitung ulang status ketepatan waktu."""
    if not version:
        return
    cr.execute("""
        UPDATE lpj_production_ok SET date_done = write_date
         WHERE state = 'done' AND date_done IS NULL
    """)
    cr.execute("""
        UPDATE lpj_production_ok SET
            delay_days = GREATEST(
                (date_done AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')::date
                - (duedate_kirim AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')::date, 0),
            ontime_status = CASE WHEN
                (date_done AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')::date
                > (duedate_kirim AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')::date
                THEN 'late' ELSE 'on_time' END
         WHERE date_done IS NOT NULL AND duedate_kirim IS NOT NULL
    """)
