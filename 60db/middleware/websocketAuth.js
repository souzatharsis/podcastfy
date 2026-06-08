const jwt = require('jsonwebtoken');
const db = require('../config/database');

/**
 * WebSocket Authentication Middleware
 * Extracts and validates JWT token from WebSocket handshake
 */
async function authenticateWebSocket(ws, req, next) {
  try {
    // Extract token from query params or headers
    const token = extractTokenFromRequest(req);

    if (!token) {
      // Don't close - just return false so API key can be tried
      return false;
    }

    // Verify JWT token
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your-secret-key');

    // Get user from database
    const userResult = await db.query(
      `SELECT id, email, full_name
       FROM users
       WHERE id = $1 AND deleted_at IS NULL`,
      [decoded.userId || decoded.id]
    );

    if (userResult.rows.length === 0) {
      return false;
    }

    const user = userResult.rows[0];

    // Resolve workspace ID from token or query params
    const queryParams = new URL(req.url, `http://${req.headers.host}`).searchParams;
    const wsId = decoded.workspaceId || decoded.workspace_id || queryParams.get('workspace_id');

    // Get workspace context and balance
    let workspaceContext = null;
    let workspaceBalance = 0;
    if (wsId) {
      const workspaceResult = await db.query(
        `SELECT w.id, w.name, w.billing_owner_id, w.amount,
                (SELECT r.name FROM roles r
                 JOIN user_workspace_roles uwr ON uwr.role_id = r.id
                 WHERE uwr.workspace_id = w.id AND uwr.user_id = $1 AND uwr.deleted_at IS NULL
                 LIMIT 1) as user_role
         FROM workspace w
         WHERE w.id = $2 AND w.deleted_at IS NULL`,
        [user.id, wsId]
      );

      if (workspaceResult.rows.length > 0) {
        workspaceContext = {
          workspace_id: workspaceResult.rows[0].id,
          workspace_name: workspaceResult.rows[0].name,
          role: workspaceResult.rows[0].user_role,
          billing_owner_id: workspaceResult.rows[0].billing_owner_id,
        };
        workspaceBalance = parseFloat(workspaceResult.rows[0].amount) || 0;
      }
    }

    // Attach user info to WebSocket instance
    ws.user = {
      id: user.id,
      email: user.email,
      full_name: user.full_name,
      credit_balance: workspaceBalance, // workspace-level balance
      current_workspace: workspaceContext,
      role: decoded.role || 'user'
    };

    return true;
  } catch (error) {
    // Don't close - let caller handle it
    if (error.name !== 'JsonWebTokenError' && error.name !== 'TokenExpiredError') {
      console.error('WebSocket authentication error:', error);
    }
    return false;
  }
}

/**
 * Parse query parameters from WebSocket request URL
 */
function parseQueryParams(req) {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    return Object.fromEntries(url.searchParams.entries());
  } catch {
    return {};
  }
}

/**
 * Extract JWT token from WebSocket request
 */
function extractTokenFromRequest(req) {
  // Parse query parameters from URL
  const queryParams = parseQueryParams(req);

  // Try query parameter first
  if (queryParams.token) {
    return queryParams.token;
  }

  // Try Authorization header
  if (req.headers && req.headers.authorization) {
    const authHeader = req.headers.authorization;
    if (authHeader.startsWith('Bearer ')) {
      return authHeader.substring(7);
    }
  }

  // Try Sec-WebSocket-Protocol header (some clients send token here)
  if (req.headers && req.headers['sec-websocket-protocol']) {
    const protocols = req.headers['sec-websocket-protocol'].split(',').map(p => p.trim());
    // Look for protocol that looks like a JWT
    const tokenProtocol = protocols.find(p => p.startsWith('ey'));
    if (tokenProtocol) {
      return tokenProtocol;
    }
  }

  return null;
}

/**
 * API Key Authentication for WebSocket
 * Alternative authentication using API keys
 */
async function authenticateWebSocketWithApiKey(ws, req) {
  try {
    // Parse query parameters from URL
    const queryParams = parseQueryParams(req);
    const apiKey = queryParams.apiKey || queryParams.api_key;

    if (!apiKey) {
      // Don't close - just return false
      return false;
    }

    if (!apiKey.startsWith('sk_')) {
      ws.close(1008, 'Invalid API key format');
      return false;
    }

    // Get API key from database with workspace and billing owner info
    const keyResult = await db.query(
      `SELECT dk.id, dk.api_key, dk.workspace_id, dk.is_active, dk.permissions,
              w.name as workspace_name, w.billing_owner_id, w.amount as workspace_balance,
              u.id as user_id, u.email, u.full_name
       FROM developer_api dk
       JOIN workspace w ON w.id = dk.workspace_id
       JOIN users u ON u.id = w.billing_owner_id
       WHERE dk.api_key = $1 AND dk.is_active = true AND u.deleted_at IS NULL`,
      [apiKey]
    );

    if (keyResult.rows.length === 0) {
      ws.close(1008, 'Invalid API key');
      return false;
    }

    const keyData = keyResult.rows[0];

    // Update last used timestamp
    await db.query(
      'UPDATE developer_api SET updated_at = NOW() WHERE id = $1',
      [keyData.id]
    );

    // Attach user info to WebSocket instance
    ws.user = {
      id: keyData.user_id,
      email: keyData.email,
      full_name: keyData.full_name,
      credit_balance: parseFloat(keyData.workspace_balance) || 0, // workspace-level balance
      current_workspace: {
        workspace_id: keyData.workspace_id,
        workspace_name: keyData.workspace_name,
        role: 'billing_owner',
        billing_owner_id: keyData.billing_owner_id,
        settings: keyData.permissions
      },
      role: 'api_key',
      api_key_id: keyData.id
    };

    return true;
  } catch (error) {
    console.error('WebSocket API key authentication error:', error);
    ws.close(1011, 'Authentication failed');
    return false;
  }
}

/**
 * Combined authentication (try JWT first, then API key)
 */
async function authenticateWebSocketAny(ws, req) {
  // Try JWT first
  const jwtAuth = await authenticateWebSocket(ws, req, () => {});
  if (jwtAuth) return true;

  // Try API key
  const apiKeyAuth = await authenticateWebSocketWithApiKey(ws, req);
  if (apiKeyAuth) return true;

  // Both failed
  ws.close(1008, 'Authentication required');
  return false;
}

/**
 * Check if user has sufficient credits for WebSocket session
 */
async function checkWebSocketCredits(ws) {
  if (!ws.user) {
    ws.close(1008, 'Not authenticated');
    return false;
  }

  const MINIMUM_CREDITS = 0.01; // Minimum required to start session

  if (ws.user.credit_balance < MINIMUM_CREDITS) {
    ws.send(JSON.stringify({
      type: 'error',
      error: 'Insufficient credits to start session',
      error_code: 'INSUFFICIENT_CREDITS',
      details: {
        required: MINIMUM_CREDITS,
        available: ws.user.credit_balance,
        shortfall: MINIMUM_CREDITS - ws.user.credit_balance
      }
    }));
    ws.close(1008, 'Insufficient credits');
    return false;
  }

  return true;
}

module.exports = {
  authenticateWebSocket,
  authenticateWebSocketWithApiKey,
  authenticateWebSocketAny,
  checkWebSocketCredits,
};
