import fs from "fs";
import path from "path";
import { execFile } from "child_process";
import { NextResponse } from "next/server";
import { WORKSPACE } from "@/lib/data";

// Hands a workspace file to the machine running the server: open it in the
// default app, reveal it in the file manager, or diff two of them. The UI is
// only ever served on localhost, but every path is still resolved and checked
// against the workspace root so a crafted request cannot reach outside it.

export const dynamic = "force-dynamic";

type Action = "open" | "reveal" | "diff";

/** Resolves a request path, rejecting anything outside the workspace. */
function safePath(p: unknown): string {
  if (typeof p !== "string" || p === "") throw new Error("Missing path");
  const abs = fs.realpathSync(path.resolve(p));
  const root = fs.realpathSync(WORKSPACE);
  if (abs !== root && !abs.startsWith(root + path.sep)) {
    throw new Error("Path is outside the workspace");
  }
  return abs;
}

function run(cmd: string, args: string[]): Promise<void> {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, (err) => (err ? reject(err) : resolve()));
  });
}

/** Whether `cmd` is on PATH — used to prefer a real diff tool when present. */
function has(cmd: string): boolean {
  const dirs = (process.env.PATH || "").split(path.delimiter);
  return dirs.some((d) => {
    try {
      fs.accessSync(path.join(d, cmd), fs.constants.X_OK);
      return true;
    } catch {
      return false;
    }
  });
}

const OPENER = process.platform === "darwin" ? "open" : "xdg-open";

async function diff(a: string, b: string): Promise<string> {
  // Editors first (they show the two files in one tab), then FileMerge.
  for (const [cmd, args] of [
    ["code", ["--diff", a, b]],
    ["cursor", ["--diff", a, b]],
    ["bcompare", [a, b]],
    ["opendiff", [a, b]],
  ] as [string, string[]][]) {
    if (!has(cmd)) continue;
    await run(cmd, args);
    return cmd;
  }
  // No diff tool installed: fall back to opening both files.
  await run(OPENER, [a]);
  await run(OPENER, [b]);
  return OPENER;
}

export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
  const action: Action = body?.action ?? "open";
  try {
    if (action === "diff") {
      const a = safePath(body?.paths?.[0]);
      const b = safePath(body?.paths?.[1]);
      const tool = await diff(a, b);
      return NextResponse.json({ ok: true, tool });
    }
    const target = safePath(body?.path);
    // `open -R` reveals the file in Finder; elsewhere just open its directory.
    if (action === "reveal") {
      if (process.platform === "darwin") await run("open", ["-R", target]);
      else await run(OPENER, [path.dirname(target)]);
    } else {
      await run(OPENER, [target]);
    }
    return NextResponse.json({ ok: true, path: target });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 400 }
    );
  }
}
