function readFileAsArrayBuffer(file: File): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onerror = () => {
      reject(new Error("Could not read the selected dataset file."));
    };

    reader.onload = () => {
      if (!(reader.result instanceof ArrayBuffer)) {
        reject(new Error("Could not read the selected dataset file."));
        return;
      }

      resolve(reader.result);
    };

    reader.readAsArrayBuffer(file);
  });
}

export async function sha256File(file: File): Promise<string> {
  const bytes = await readFileAsArrayBuffer(file);
  const digest = await crypto.subtle.digest("SHA-256", bytes);

  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
