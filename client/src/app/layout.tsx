import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SubmissionProvider } from "@/context/SubmissionContext";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { Toaster } from "@/app/toast";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Commission Tracker - Professional Financial Document Processing",
  description: "Premium SaaS platform for commission tracking and financial document extraction with AI-powered processing",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body
        className={`${inter.variable} font-sans antialiased h-full bg-slate-50`}
        suppressHydrationWarning={true}
      >
        <ThemeProvider>
          <AuthProvider>
            <SubmissionProvider>
              {children}
            </SubmissionProvider>
          </AuthProvider>
        </ThemeProvider>
        <Toaster />
      </body>
    </html>
  );
}
