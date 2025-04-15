import { ThemeProvider } from "@/components/theme-provider";
import { ChatProvider } from "@/lib/store/ChatContext";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KNet: Deep Research",
  description: "KNet is a deep research tool that uses AI to help you find answers to your questions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <ChatProvider>{children}</ChatProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
