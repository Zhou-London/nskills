import type { Metadata } from "next";
import Link from "next/link";
import { listSkillNames } from "@/lib/data";
import "./globals.css";

export const metadata: Metadata = {
  title: "SkillsTester",
  description: "Acceptance testing for Claude skills",
};

export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const skills = listSkillNames();
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <div className="nav-inner">
            <Link href="/" className="wordmark">
              Skills<span>Tester</span>
            </Link>
            <div className="nav-links">
              {skills.map((s) => (
                <Link key={s} href={`/skills/${s}`} className="nav-link">
                  {s}
                </Link>
              ))}
            </div>
          </div>
        </nav>
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
