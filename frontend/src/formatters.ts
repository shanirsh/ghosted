export function formatInstance(instance: any, defaultRegion = 'us-east-1'): string {
  const id =
    instance['Instance ID'] || instance.id || instance.instance_id || instance.InstanceId || 'Unknown';

  let name = 'N/A';
  if (instance.Tags && typeof instance.Tags === 'object' && !Array.isArray(instance.Tags)) {
    name = instance.Tags.Name || 'N/A';
  } else if (instance.Tags && Array.isArray(instance.Tags)) {
    name = instance.Tags.find((t: any) => t.Key === 'Name')?.Value || 'N/A';
  } else if (instance.tags && typeof instance.tags === 'object') {
    name = instance.tags.Name || 'N/A';
  }
  name = instance.name || instance.Name || name;

  const type =
    instance['Instance Type'] || instance.type || instance.instance_type || instance.InstanceType || 'Unknown';
  const state =
    instance['State'] || instance.state || (instance.State && instance.State.Name) || instance.status || 'Unknown';

  let az =
    instance['Availability Zone'] ||
    instance.az ||
    instance.availability_zone ||
    instance.AvailabilityZone ||
    (instance.Placement && instance.Placement.AvailabilityZone) ||
    '';

  const region = az ? az.substring(0, az.length - 1) : (instance.region || defaultRegion);
  if (!az) az = region + 'a';

  const publicIp = instance['Public IP'] || instance.public_ip || instance.PublicIpAddress || 'N/A';
  const privateIp = instance['Private IP'] || instance.private_ip || instance.PrivateIpAddress || 'N/A';

  const consoleUrl =
    instance.console_link ||
    `https://${region}.console.aws.amazon.com/ec2/v2/home?region=${region}#InstanceDetails:instanceId=${id}`;

  return `- **ID:** ${id}\n  - **Name:** ${name}\n  - **Type:** ${type}\n  - **State:** ${state}\n  - **AZ:** ${az}\n  - **Public IP:** ${publicIp}\n  - **Private IP:** ${privateIp}\n  - **Console:** [Open in AWS Console](${consoleUrl})\n`;
}

export function formatBucketDetailed(bucket: any): string {
  const name = bucket.name || bucket.Name || bucket.bucket_name || 'Unknown';
  const creationDate = bucket.creation_date || bucket.CreationDate || 'N/A';
  const region = bucket.region || bucket.Region || 'N/A';
  const versioning = bucket.versioning || 'N/A';
  const consoleUrl =
    bucket.console_link || `https://s3.console.aws.amazon.com/s3/buckets/${name}?region=${region}`;

  return `- **Bucket:** ${name}\n  **Created:** ${creationDate}\n  **Region:** ${region}\n  **Versioning:** ${versioning}\n  **Console:** [Open in AWS Console](${consoleUrl})\n`;
}

export function formatBucketSimple(bucketName: any): string {
  const name =
    typeof bucketName === 'object'
      ? bucketName.name || bucketName.Name || bucketName.bucket_name || 'Unknown'
      : bucketName || 'Unknown';
  const consoleUrl = `https://s3.console.aws.amazon.com/s3/buckets/${name}?region=us-east-1`;

  return `- **Bucket:** ${name}\n  **Created:** N/A\n  **Region:** us-east-1\n  **Console:** [Open in AWS Console](${consoleUrl})\n`;
}

export function formatS3Object(obj: any): string {
  const key = obj.key || obj.Key || obj.name || 'Unknown';
  const size = obj.size || obj.Size || 'N/A';
  const lastModified = obj.last_modified || obj.LastModified || 'N/A';
  return `- Key: ${key} | Size: ${size} bytes | Last Modified: ${lastModified}`;
}

export function findInstances(data: any): any[] {
  if (data.instances && Array.isArray(data.instances) && data.instances.length > 0) return data.instances;
  const nested = data.data && typeof data.data === 'object' ? data.data : null;
  const result = data.result && typeof data.result === 'object' ? data.result : null;
  if (nested?.items && Array.isArray(nested.items) && nested.items[0]?.id?.startsWith?.('i-')) return nested.items;
  if (Array.isArray(nested) && nested.length > 0 && nested[0]?.id?.startsWith?.('i-')) return nested;
  if (result?.instances && Array.isArray(result.instances)) return result.instances;
  if (nested?.instances && Array.isArray(nested.instances)) return nested.instances;
  return [];
}

export function findBuckets(data: any): { buckets: any[]; details: any[] } {
  const sources = [data, data.result, data.data].filter(
    (s) => s && typeof s === 'object' && !Array.isArray(s)
  );
  for (const src of sources) {
    if (src.buckets && Array.isArray(src.buckets) && src.buckets.length > 0) {
      return { buckets: src.buckets, details: src.bucket_details || [] };
    }
  }
  return { buckets: [], details: [] };
}

export function findS3Objects(data: any): any[] {
  const sources = [data, data.result, data.data].filter(
    (s) => s && typeof s === 'object' && !Array.isArray(s)
  );
  for (const src of sources) {
    const objs = src.objects || src.contents || src.Contents;
    if (objs && Array.isArray(objs) && objs.length > 0) return objs;
  }
  return [];
}
