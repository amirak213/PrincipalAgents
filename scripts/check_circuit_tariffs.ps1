param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 5433,
    [string]$Database = "dourbia",
    [string]$User = "dourbia"
)

$query = @"
SELECT
    COUNT(*) AS total_monuments,
    COUNT(*) FILTER (WHERE price_resident IS NULL) AS resident_null,
    COUNT(*) FILTER (WHERE price_student IS NULL) AS student_null,
    COUNT(*) FILTER (WHERE price_foreign IS NULL) AS foreign_null
FROM public.monuments;
"@

& psql -h $HostName -p $Port -U $User -d $Database -c $query
if ($LASTEXITCODE -ne 0) {
    throw "Tariff check failed (psql exit code $LASTEXITCODE)."
}