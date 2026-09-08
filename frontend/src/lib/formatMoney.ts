export function formatMoney(amount: number, currency: string): string {
  const numericAmount = Number.isFinite(amount) ? amount : 0;
  if (currency === "IDR") {
    return `Rp ${numericAmount.toLocaleString("id-ID")}`;
  }
  return `${currency} ${numericAmount.toLocaleString("en-US")}`;
}