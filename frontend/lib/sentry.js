/**
 * Sentry helpers for manual error/event capture throughout the app.
 *
 * Usage:
 *   import { captureError, captureMessage, withSentryContext } from '../lib/sentry';
 *
 *   captureError(err, { tags: { section: 'repricing' }, extra: { productId: 123 } });
 *   captureMessage('Unexpected empty response from /api/products', 'warning');
 */

import * as Sentry from '@sentry/nextjs';

/**
 * Capture an error with optional context.
 * @param {Error|unknown} error
 * @param {{ tags?: Record<string,string>, extra?: Record<string,unknown>, level?: string }} [ctx]
 */
export function captureError(error, ctx = {}) {
  Sentry.withScope((scope) => {
    if (ctx.tags)  scope.setTags(ctx.tags);
    if (ctx.extra) scope.setExtras(ctx.extra);
    if (ctx.level) scope.setLevel(ctx.level);
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
  });
}

/**
 * Capture a plain message (no error object).
 * @param {string} message
 * @param {'fatal'|'error'|'warning'|'info'|'debug'} [level]
 */
export function captureMessage(message, level = 'info') {
  Sentry.captureMessage(message, level);
}

/**
 * Wrap an async function so any thrown error is captured by Sentry before re-throwing.
 * @template T
 * @param {() => Promise<T>} fn
 * @param {{ tags?: Record<string,string>, extra?: Record<string,unknown> }} [ctx]
 * @returns {Promise<T>}
 */
export async function withSentryContext(fn, ctx = {}) {
  try {
    return await fn();
  } catch (err) {
    captureError(err, ctx);
    throw err;
  }
}

/**
 * Add a breadcrumb — a trail of events leading up to an error.
 * Helpful for seeing what the user did before something broke.
 * @param {string} message
 * @param {{ category?: string, data?: Record<string,unknown>, level?: string }} [opts]
 */
export function addBreadcrumb(message, opts = {}) {
  Sentry.addBreadcrumb({
    message,
    category: opts.category || 'app',
    data: opts.data,
    level: opts.level || 'info',
  });
}
