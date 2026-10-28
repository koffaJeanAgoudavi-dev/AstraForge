import { Request, Response, NextFunction } from 'express';
import { adminAuth } from '../lib/firebase-admin.ts';
import { DecodedIdToken } from 'firebase-admin/auth';
import { getOrCreateUser } from '../db/users.ts';

export interface AuthRequest extends Request {
  user?: DecodedIdToken & { dbUserId?: number };
}

export const requireAuth = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Unauthorized: Missing token' });
  }

  const token = authHeader.split('Bearer ')[1];
  try {
    const decodedToken = await adminAuth.verifyIdToken(token);
    let dbUser;
    if (decodedToken.email) {
      try {
        dbUser = await getOrCreateUser(decodedToken.uid, decodedToken.email);
      } catch (e) {
        console.error('Warning: could not sync user to DB:', e);
      }
    }
    req.user = {
      ...decodedToken,
      dbUserId: dbUser?.id,
    };
    next();
  } catch (error) {
    console.error('Error verifying Firebase ID token:', error);
    return res.status(401).json({ error: 'Unauthorized: Invalid token' });
  }
};

export const optionalAuth = async (
  req: AuthRequest,
  res: Response,
  next: NextFunction
) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return next();
  }

  const token = authHeader.split('Bearer ')[1];
  try {
    const decodedToken = await adminAuth.verifyIdToken(token);
    let dbUser;
    if (decodedToken.email) {
      try {
        dbUser = await getOrCreateUser(decodedToken.uid, decodedToken.email);
      } catch (e) {
        console.error('Warning: could not sync user to DB:', e);
      }
    }
    req.user = {
      ...decodedToken,
      dbUserId: dbUser?.id,
    };
  } catch (error) {
    // If token is invalid or expired, continue as guest
    console.warn('Optional auth token verification skipped:', error);
  }
  next();
};
