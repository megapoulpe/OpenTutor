# Supabase PostgreSQL trust anchor

`supabase-prod-ca-2021.crt` is the public production CA certificate linked by
Supabase Studio, downloaded over verified HTTPS from:

https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt

Official Studio download configuration:
https://github.com/supabase/supabase/blob/master/apps/studio/hooks/custom-content/custom-content.json
(`ssl:certificate_url`, with `env=prod`).

Downloaded 2026-11-07. Expires 2031-04-26 10:56:53 UTC.
SHA-256 of the downloaded file:
`700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`

This public certificate contains no private key. It is packaged with the API
for offline startup and shared by the API and Alembic. Keep `verify-full` enabled
when updating it from the official source before expiry or a Supabase CA rotation.
