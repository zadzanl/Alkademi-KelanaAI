import type { Metadata } from "next";
import { Instrument_Serif, Source_Sans_3 } from "next/font/google";
import "./globals.css";
import { AuthHeader } from "../components/AuthHeader";

const instrumentSerif = Instrument_Serif({
  weight: "400",
  style: "normal",
  subsets: ["latin"],
  display: "swap",
  variable: "--font-instrument-serif",
});

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-source-sans",
});

export const metadata: Metadata = {
  title: "KelanaAI | Plan a trip that feels like you",
  description: "Build a grounded trip snapshot with KelanaAI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('kelana_theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`,
          }}
        />
      </head>
      <body
        className={`${instrumentSerif.variable} ${sourceSans.variable} antialiased`}
      >
        <div className="border-b border-rule bg-paper px-5 py-2 text-right sm:px-8"><AuthHeader /></div>
        {children}
      </body>
    </html>
  );
}
