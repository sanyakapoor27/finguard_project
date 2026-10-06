import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinGuard CoCopilot",
  description: "Enterprise Risk, Liquidity & AML Terminal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
