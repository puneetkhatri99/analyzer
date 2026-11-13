// A one-time password the admin hands over; the user must replace it at first sign-in.
// No look-alike characters (0/O, 1/l/I), so it can be read out or typed from a screen.
const CHARS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789";

export function newPassword(length = 12) {
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(bytes, (b) => CHARS[b % CHARS.length]).join("");
}
