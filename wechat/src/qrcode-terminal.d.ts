declare module "qrcode-terminal" {
  const mod: {
    generate(text: string, opts?: { small?: boolean }, cb?: (qr: string) => void): void;
  };
  export default mod;
}
