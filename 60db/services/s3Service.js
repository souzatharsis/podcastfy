// Central S3 client and upload/delete/signing helpers.
//
// All file storage in 60db-api flows through this module. Controllers should
// never use `fs` + `/uploads/...` for user-generated content — call these
// helpers so we get a consistent key layout, public-vs-private ACLs, and a
// single place to swap providers (S3, R2, MinIO) later.
//
// Env:
//   AWS_REGION                   e.g. ap-south-1
//   AWS_ACCESS_KEY_ID
//   AWS_SECRET_ACCESS_KEY
//   AWS_S3_BUCKET                bucket name
//   S3_PUBLIC_URL                (optional) CDN base, e.g. https://cdn.60db.ai
//                                falls back to the virtual-hosted S3 URL
//   S3_SIGNED_URL_EXPIRES        (optional) default signed URL TTL, seconds
//   AWS_S3_ENDPOINT              (optional) for R2 / MinIO / Spaces
//   AWS_S3_FORCE_PATH_STYLE      (optional) "true" for MinIO

const fs = require("fs");
const { Readable } = require("stream");
const {
  S3Client,
  PutObjectCommand,
  DeleteObjectCommand,
  DeleteObjectsCommand,
  ListObjectsV2Command,
  HeadObjectCommand,
  GetObjectCommand,
} = require("@aws-sdk/client-s3");
const {
  getSignedUrl: awsGetSignedUrl,
} = require("@aws-sdk/s3-request-presigner");

const REGION = process.env.AWS_REGION || "us-east-1";
const BUCKET = process.env.AWS_S3_BUCKET;
const ENDPOINT = process.env.AWS_S3_ENDPOINT || undefined;
const FORCE_PATH_STYLE =
  (process.env.AWS_S3_FORCE_PATH_STYLE || "").toLowerCase() === "true";
const DEFAULT_SIGNED_EXPIRES = parseInt(
  process.env.S3_SIGNED_URL_EXPIRES || "3600",
  10,
);

if (!BUCKET) {
  console.warn(
    "[s3Service] AWS_S3_BUCKET is not set — S3 uploads will fail. Check .env",
  );
}

const client = new S3Client({
  region: REGION,
  ...(ENDPOINT ? { endpoint: ENDPOINT, forcePathStyle: FORCE_PATH_STYLE } : {}),
  credentials:
    process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY
      ? {
          accessKeyId: process.env.AWS_ACCESS_KEY_ID,
          secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
        }
      : undefined, // fall through to SDK default credential chain (IAM role)
});

function publicBase() {
  if (process.env.S3_PUBLIC_URL) {
    return process.env.S3_PUBLIC_URL.replace(/\/+$/, "");
  }
  if (ENDPOINT) {
    // R2/MinIO style
    return `${ENDPOINT.replace(/\/+$/, "")}/${BUCKET}`;
  }
  return `https://${BUCKET}.s3.${REGION}.amazonaws.com`;
}

function publicUrl(key) {
  if (!key) return null;
  return `${publicBase()}/${key.replace(/^\/+/, "")}`;
}

// Given a previously-stored URL (CDN, S3 virtual-hosted, or legacy
// "/uploads/..." path), return the S3 object key — or null if it wasn't
// produced by us.
function keyFromUrl(urlOrPath) {
  if (!urlOrPath) return null;
  // Already a bare key (no leading slash, no scheme) — trust it.
  if (!/^https?:\/\//i.test(urlOrPath) && !urlOrPath.startsWith("/")) {
    return urlOrPath;
  }
  const base = publicBase();
  if (urlOrPath.startsWith(base + "/")) {
    return urlOrPath.slice(base.length + 1);
  }
  // Legacy local path ("/uploads/...") — caller has to handle separately.
  if (urlOrPath.startsWith("/uploads/")) {
    return null;
  }
  // Some other S3 URL — try to parse generically.
  try {
    const u = new URL(urlOrPath);
    if (u.hostname.includes("amazonaws.com") || u.hostname.endsWith(BUCKET)) {
      // Virtual-hosted style: /key
      return u.pathname.replace(/^\/+/, "");
    }
  } catch (_) {}
  return null;
}

// --- Uploads ---------------------------------------------------------------

// Note on ACLs: modern S3 buckets default to "Bucket owner enforced" which
// rejects per-object ACLs. Public access must be granted by a bucket policy
// instead. We keep the `isPublic` flag for call-site intent (and for the
// returned URL), but we do NOT set an ACL on the PutObject. If you want
// public read for a path, add a bucket policy like:
//   { "Effect":"Allow","Principal":"*","Action":"s3:GetObject",
//     "Resource":"arn:aws:s3:::sixty-db/users/*/voices/*" }
async function putObject({ key, body, contentType, isPublic = false, metadata }) {
  if (!BUCKET) throw new Error("AWS_S3_BUCKET is not configured");
  const cmd = new PutObjectCommand({
    Bucket: BUCKET,
    Key: key,
    Body: body,
    ContentType: contentType,
    ...(metadata ? { Metadata: metadata } : {}),
  });
  await client.send(cmd);
  return { key, url: isPublic ? publicUrl(key) : null };
}

async function uploadBuffer(key, buffer, contentType, opts = {}) {
  return putObject({ key, body: buffer, contentType, ...opts });
}

async function uploadFile(key, filePath, contentType, opts = {}) {
  const body = fs.createReadStream(filePath);
  return putObject({ key, body, contentType, ...opts });
}

async function uploadStream(key, stream, contentType, opts = {}) {
  const body = stream instanceof Readable ? stream : Readable.from(stream);
  return putObject({ key, body, contentType, ...opts });
}

// --- Delete ---------------------------------------------------------------

async function deleteObject(key) {
  if (!key) return;
  await client.send(new DeleteObjectCommand({ Bucket: BUCKET, Key: key }));
}

async function deletePrefix(prefix) {
  let ContinuationToken;
  do {
    const list = await client.send(
      new ListObjectsV2Command({
        Bucket: BUCKET,
        Prefix: prefix,
        ContinuationToken,
      }),
    );
    const contents = list.Contents || [];
    if (contents.length > 0) {
      await client.send(
        new DeleteObjectsCommand({
          Bucket: BUCKET,
          Delete: { Objects: contents.map((o) => ({ Key: o.Key })) },
        }),
      );
    }
    ContinuationToken = list.IsTruncated ? list.NextContinuationToken : undefined;
  } while (ContinuationToken);
}

// --- Read / signed URLs ---------------------------------------------------

async function headObject(key) {
  try {
    return await client.send(new HeadObjectCommand({ Bucket: BUCKET, Key: key }));
  } catch (err) {
    if (err?.$metadata?.httpStatusCode === 404) return null;
    throw err;
  }
}

async function exists(key) {
  return (await headObject(key)) !== null;
}

async function getObjectStream(key) {
  const out = await client.send(
    new GetObjectCommand({ Bucket: BUCKET, Key: key }),
  );
  return out.Body; // Readable
}

async function getObjectBuffer(key) {
  const body = await getObjectStream(key);
  const chunks = [];
  for await (const chunk of body) chunks.push(chunk);
  return Buffer.concat(chunks);
}

async function getSignedUrl(key, expiresIn = DEFAULT_SIGNED_EXPIRES) {
  return awsGetSignedUrl(
    client,
    new GetObjectCommand({ Bucket: BUCKET, Key: key }),
    { expiresIn },
  );
}

async function getPresignedPutUrl(
  key,
  contentType,
  expiresIn = DEFAULT_SIGNED_EXPIRES,
) {
  return awsGetSignedUrl(
    client,
    new PutObjectCommand({ Bucket: BUCKET, Key: key, ContentType: contentType }),
    { expiresIn },
  );
}

module.exports = {
  client,
  BUCKET,
  REGION,
  publicUrl,
  publicBase,
  keyFromUrl,
  uploadBuffer,
  uploadFile,
  uploadStream,
  deleteObject,
  deletePrefix,
  headObject,
  exists,
  getObjectStream,
  getObjectBuffer,
  getSignedUrl,
  getPresignedPutUrl,
};
