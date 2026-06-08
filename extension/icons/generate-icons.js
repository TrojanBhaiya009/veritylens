// 生成简单的 PNG 图标（纯 Node.js，无依赖）
const fs = require('fs');

function createPNG(width, height, color) {
  // PNG 签名
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  
  // IHDR chunk
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // color type: RGB
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace
  
  const ihdrChunk = createChunk('IHDR', ihdr);
  
  // IDAT chunk (图像数据)
  const rawData = Buffer.alloc(width * height * 3);
  for (let i = 0; i < width * height; i++) {
    rawData[i * 3] = color.r;
    rawData[i * 3 + 1] = color.g;
    rawData[i * 3 + 2] = color.b;
  }
  
  // 添加 filter byte (0 = None)
  const filteredData = Buffer.alloc(rawData.length + height);
  for (let y = 0; y < height; y++) {
    filteredData[y * (width * 3 + 1)] = 0; // filter byte
    rawData.copy(filteredData, y * (width * 3 + 1) + 1, y * width * 3, (y + 1) * width * 3);
  }
  
  const zlib = require('zlib');
  const compressed = zlib.deflateSync(filteredData);
  const idatChunk = createChunk('IDAT', compressed);
  
  // IEND chunk
  const iendChunk = createChunk('IEND', Buffer.alloc(0));
  
  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

function createChunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  
  const typeBuffer = Buffer.from(type, 'ascii');
  
  const crcData = Buffer.concat([typeBuffer, data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(crcData), 0);
  
  return Buffer.concat([length, typeBuffer, data, crc]);
}

function crc32(buf) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) {
    crc ^= buf[i];
    for (let j = 0; j < 8; j++) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xEDB88320 : 0);
    }
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

// 生成图标（紫色渐变）
const icon48 = createPNG(48, 48, { r: 99, g: 102, b: 241 });
const icon128 = createPNG(128, 128, { r: 99, g: 102, b: 241 });

fs.writeFileSync('icon-48.png', icon48);
fs.writeFileSync('icon-128.png', icon128);

console.log('✅ 图标已生成：icon-48.png, icon-128.png');
