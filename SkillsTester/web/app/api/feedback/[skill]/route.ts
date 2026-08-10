import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";
import { WORKSPACE, isSkill, getSkillData } from "@/lib/data";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ skill: string }> }
) {
  const { skill } = await params;
  if (!isSkill(skill)) {
    return NextResponse.json({ error: "Unknown skill" }, { status: 404 });
  }
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
  if (!Array.isArray(body?.reviews)) {
    return NextResponse.json(
      { error: "Body must contain a reviews array" },
      { status: 400 }
    );
  }
  const data = getSkillData(skill);
  if (!data || data.iteration === 0) {
    return NextResponse.json({ error: "No iteration found" }, { status: 404 });
  }
  const now = new Date().toISOString();
  const payload = {
    skill,
    iteration: data.iteration,
    status: "complete",
    submitted_at: now,
    reviews: body.reviews.map((r: any) => ({
      run_id: String(r.run_id ?? ""),
      feedback: String(r.feedback ?? ""),
      timestamp: now,
    })),
  };
  const dest = path.join(
    WORKSPACE,
    skill,
    `iteration-${data.iteration}`,
    "feedback.json"
  );
  fs.writeFileSync(dest, JSON.stringify(payload, null, 2));
  return NextResponse.json({ ok: true, saved_to: dest });
}
