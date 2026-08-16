import { OTA } from "@shared/constants.ts";

const DATA_SERVICE_UUID = OTA.DATA_SERVICE.toString(16).padStart(4, "0");
const OTA_SERVICE_UUID = OTA.OTA_SERVICE.toString(16).padStart(4, "0");

function le32(v: number): Uint8Array {
  return new Uint8Array([v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >>> 24) & 0xff]);
}

function le16(v: number): Uint8Array {
  return new Uint8Array([v & 0xff, (v >> 8) & 0xff]);
}

function dataFrame(cmd: number, dir: number, payload: Uint8Array): Uint8Array {
  const len = payload.length + 1;
  return new Uint8Array([
    0x6f, cmd, dir, ...le16(len), ...payload, 0x8f,
  ]);
}

export interface UploadProgress {
  phase: string;
  piece: number;
  totalPieces: number;
  percent: number;
}

export async function uploadWatchface(
  binData: Uint8Array,
  onProgress: (p: UploadProgress) => void,
): Promise<void> {
  const device = await (navigator as any).bluetooth.requestDevice({
    filters: [{ namePrefix: "KW80" }],
    optionalServices: [DATA_SERVICE_UUID, OTA_SERVICE_UUID],
  });

  const server = await device.gatt.connect();

  // Get OTA address from DATA service
  const dataService = await server.getPrimaryService(DATA_SERVICE_UUID);
  const dataWrite = await dataService.getCharacteristic(`0x${OTA.DATA_WRITE.toString(16)}`);
  const dataRead = await dataService.getCharacteristic(`0x${OTA.DATA_READ.toString(16)}`);

  // Request OTA address for slot 1
  await dataWrite.writeValueWithoutResponse(
    dataFrame(0x1e, 0x70, new Uint8Array([0x01, ...le32(1)])),
  );

  // Read response
  let otaAddress = new Uint8Array([0x00, 0x00, 0xc8, 0x00]);
  dataRead.addEventListener("characteristicvaluechanged", (event: any) => {
    const value = new Uint8Array(event.target.value.buffer);
    if (value.length > 7) {
      otaAddress = value.subarray(7, 11);
    }
  });
  await dataRead.startNotifications();
  await new Promise((r) => setTimeout(r, 500));
  await dataRead.stopNotifications();

  // Switch to OTA service
  const otaService = await server.getPrimaryService(OTA_SERVICE_UUID);
  const otaCtrl = await otaService.getCharacteristic(`0x${OTA.OTA_CTRL.toString(16)}`);
  const otaData = await otaService.getCharacteristic(`0x${OTA.OTA_DATA.toString(16)}`);

  const totalLen = binData.length;
  const totalPieces = Math.ceil(totalLen / OTA.PIECE);

  // Compute CRC
  let crc = 0xffff;
  for (const b of binData) {
    let i2 = (((crc << 8) | ((crc >> 8) & 0xff)) & 0xffff) ^ b;
    let i3 = i2 ^ (((i2 & 0xff) >> 4) & 0xffff);
    let i4 = i3 ^ ((i3 << 12) & 0xffff);
    crc = i4 ^ (((i4 & 0xff) << 5) & 0xffff);
  }
  crc = crc & 0xffff;

  let resolveWait: (() => void) | null = null;
  let currentPiece = 0;

  const handleNotify = async (event: any) => {
    const value = new Uint8Array(event.target.value.buffer);
    const op = value[0];
    const status = value[1];
    const sub = value[2];

    if (status === 0x3a || (status === 0xff && op !== 5)) {
      throw new Error(`OTA failed: op=${op} status=${status.toString(16)}`);
    }

    switch (op) {
      case 1: {
        // send settings frame
        const settings = new Uint8Array([
          0x02, OTA.TYPE_PICTURE,
          ...otaAddress,
          ...le32(totalLen),
          crc & 0xff, (crc >> 8) & 0xff, 0x00, 0x00,
          OTA.BATCH,
        ]);
        await otaCtrl.writeValueWithoutResponse(settings);
        break;
      }
      case 2:
        currentPiece = 0;
        await sendPiece(0);
        onProgress({ phase: "Uploading", piece: 0, totalPieces, percent: 0 });
        break;
      case 3:
        if (sub === 2) {
          currentPiece++;
          await sendPiece(currentPiece);
          onProgress({
            phase: "Uploading",
            piece: currentPiece,
            totalPieces,
            percent: Math.round((currentPiece / totalPieces) * 90),
          });
        } else if (sub === 4) {
          await otaCtrl.writeValueWithoutResponse(new Uint8Array([0x04]));
          onProgress({ phase: "Verifying CRC", piece: currentPiece, totalPieces, percent: 95 });
        }
        break;
      case 4:
        await otaCtrl.writeValueWithoutResponse(new Uint8Array([0x05]));
        onProgress({ phase: "Completing", piece: totalPieces, totalPieces, percent: 98 });
        break;
      case 5:
        onProgress({ phase: "Complete", piece: totalPieces, totalPieces, percent: 100 });
        if (resolveWait) resolveWait();
        break;
    }
  };

  async function sendPiece(pieceIdx: number) {
    const offset = pieceIdx * OTA.PIECE;
    const end = Math.min(offset + OTA.PIECE, totalLen);
    let chunkOffset = offset;
    while (chunkOffset < end) {
      const chunk = binData.subarray(chunkOffset, chunkOffset + OTA.MTU);
      await otaData.writeValueWithoutResponse(chunk);
      chunkOffset += OTA.MTU;
    }
  }

  otaCtrl.addEventListener("characteristicvaluechanged", handleNotify);
  await otaCtrl.startNotifications();

  // Start
  await otaCtrl.writeValueWithoutResponse(new Uint8Array([0x01, ...le32(totalLen)]));
  onProgress({ phase: "Starting", piece: 0, totalPieces, percent: 1 });

  await new Promise<void>((resolve) => { resolveWait = resolve; });

  otaCtrl.removeEventListener("characteristicvaluechanged", handleNotify);
  device.gatt.disconnect();

  function le32Local(v: number): Uint8Array {
    return new Uint8Array([v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >>> 24) & 0xff]);
  }
}

export function isWebBluetoothSupported(): boolean {
  return typeof (navigator as any).bluetooth !== "undefined";
}
