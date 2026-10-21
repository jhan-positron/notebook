SELECT
  name,
  COUNT(*) AS n,
  printf('%.3f', SUM(dur) / 1000000.0) AS total_ms,
  printf('%.6f', AVG(dur) / 1000000.0) AS avg_ms,
  printf('%.6f', MAX(dur) / 1000000.0) AS max_ms
FROM slice
WHERE name IN (
  'Attn residual and RMS norm',
  'Post attn prepare',
  'launch_hw_attn',
  'prep_hw_attn',
  'xfer_gof',
  'gof_populate',
  'gof_rodeo'
)
GROUP BY name
ORDER BY name;
