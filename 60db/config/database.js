const { Pool } = require("pg");
require("dotenv").config();

const logger = require("../utils/logger");

const pool = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Test database connection
pool.on("connect", () => {
  console.log("Connected to PostgreSQL database");
  logger.logBusinessEvent("database_connected", {
    "db.host": process.env.DB_HOST,
    "db.port": process.env.DB_PORT,
    "db.name": process.env.DB_NAME,
  });
});

pool.on("error", (err) => {
  console.error("Database connection error:", err);
  logger.error("Database connection error", {
    "error.message": err.message,
    "error.stack": err.stack,
    "error.code": err.code,
    "log.type": "database_error",
  });
  process.exit(-1);
});

// Enhanced query function with telemetry tracking
const queryWithTelemetry = async (text, params) => {
  const start = Date.now();
  const queryId = `db_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

  try {
    logger.debug("Database query started", {
      "db.query_id": queryId,
      "db.query": text.substring(0, 500),
      "db.params": JSON.stringify(params || []).substring(0, 200),
      "log.type": "db_query_start",
    });

    const result = await pool.query(text, params);
    const duration = Date.now() - start;

    // Log successful query
    logger.logDbQuery(text, duration, null);

    // Log query details
    logger.debug("Database query completed", {
      "db.query_id": queryId,
      "db.row_count": result.rowCount,
      "db.duration_ms": duration,
      "log.type": "db_query_end",
    });

    return result;
  } catch (error) {
    const duration = Date.now() - start;

    // Log failed query
    logger.logDbQuery(text, duration, error);

    // Log query error details
    logger.error("Database query failed", {
      "db.query_id": queryId,
      "db.query": text.substring(0, 500),
      "error.message": error.message,
      "error.code": error.code,
      "error.stack": error.stack,
      "db.duration_ms": duration,
      "log.type": "db_query_error",
    });

    throw error;
  }
};

// Transaction wrapper with telemetry
const transaction = async (callback) => {
  const client = await pool.connect();
  const transactionId = `txn_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

  try {
    await client.query("BEGIN");

    logger.info("Database transaction started", {
      "db.transaction_id": transactionId,
      "log.type": "db_transaction_start",
    });

    const result = await callback(client);

    await client.query("COMMIT");

    logger.info("Database transaction committed", {
      "db.transaction_id": transactionId,
      "log.type": "db_transaction_commit",
    });

    return result;
  } catch (error) {
    await client.query("ROLLBACK");

    logger.error("Database transaction rolled back", {
      "db.transaction_id": transactionId,
      "error.message": error.message,
      "error.code": error.code,
      "log.type": "db_transaction_rollback",
    });

    throw error;
  } finally {
    client.release();
  }
};

module.exports = {
  pool,
  query: queryWithTelemetry,
  transaction,
};
