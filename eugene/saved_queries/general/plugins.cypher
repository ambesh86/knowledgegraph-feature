SHOW procedures;
// or
SHOW procedures WHERE name STARTS WITH 'apoc';
// see gds version
CALL gds.debug.sysInfo()
YIELD
  key,
  value
