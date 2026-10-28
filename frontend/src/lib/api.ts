export type Role = "federation" | "athlete" | "coach" | "judge";
export type Me = { id: number; email: string; full_name: string; roles: Role[]; active_role: Role | null };
export type Discipline = { id: number; code: string; name: string };
export type Dashboard = { role: Role; metrics: { label: string; value: string }[]; guardian_status: string | null };
export type AgeGroup = { id: number; name: string; min_age: number; max_age: number };
export type CalendarEntry = { id: number; source: "ekp" | "regional"; entry_number: string; title: string; year: number; reference_url: string };
export type MetricField = { key: string; label: string; type: "number" | "string"; required: boolean };
export type ProtocolTemplate = { id: number; discipline: number; discipline_code: string; version: number; name: string; competition_type: string; rule_version: string; effective_from: string | null; metric_fields: MetricField[]; columns: string[]; sections: string[]; signature_roles: string[]; sort: { key: string; direction: "asc" | "desc" }; source_url: string; source_verified: boolean; source_note: string };
export type CompetitionStage = { order: number; name: string; format: "online" | "in_person" | "hybrid"; starts_at: string; ends_at: string };
export type Competition = { id: number; title: string; discipline: number; discipline_name: string; age_groups: number[]; age_group_details: AgeGroup[]; level: string; competition_type: string; format: "online" | "in_person" | "hybrid"; starts_at: string; ends_at: string; registration_deadline: string; age_reference_date: string; allow_ties: boolean; location: string; regulations: string; calendar_entry: number | null; template: number; state: "draft" | "published" | "closed"; stages: CompetitionStage[] };
export type Application = { id: number; competition: number; athlete: number; athlete_name: string; age_group: number; submitted_by: number; status: "pending" | "approved" | "rejected"; decision_reason: string };
export type JudgeAssignment = { id: number; competition: number; judge: number; judge_name: string; role_label: string };
export type Result = { id: number; application: number; status: "classified" | "no_show" | "unclassified" | "disqualified"; place: number | null; score: string | null; metrics: Record<string, string | number>; validated_by: number | null; updated_by: number; updated_at: string };
export type ProtocolSnapshot = { competition_id: number; competition_title: string; discipline: string; template_id: number; template_version: number; source_verified: boolean; source_note: string; source_url: string; sections: string[]; signature_roles: string[]; sort: { key: string; direction: string }; metadata: { level: string; competition_type: string; format: string; starts_at: string; ends_at: string; age_reference_date: string; location: string; calendar_entry: string | null; stages: CompetitionStage[] }; judges: { name: string; role: string }[]; columns: { key: string; label: string }[]; rows: (Record<string, string | number | null> & { application_id: number; athlete_id: number; status: string })[] };
export type ProtocolPublication = { id: number; version: number; snapshot: ProtocolSnapshot; correction_reason: string; published_at: string };
export type CoachLink = { id: number; coach: number; coach_name: string; athlete: number | null; athlete_name: string; discipline: number; status: "pending" | "confirmed" | "rejected" };
export type RatingContribution = { competition_id: number; competition_title: string; competition_level: string; publication_id: number; publication_version: number; placement: number; awarded_points: string; age_group: string; source_snapshot: Record<string, unknown> };
export type AthleteRating = { id: number; athlete: number; athlete_name: string; season: number; discipline: number; discipline_code: string; discipline_name: string; base_score: string; prize_count: number; coefficient: string; rating_score: string; calculated_at: string; placement: number; breakdown: RatingContribution[] };
export type RatingOptions = { seasons: { id: number; year: number; name: string; is_active: boolean }[]; disciplines: { id: number; code: string; name: string }[]; age_groups: { id: number; name: string; min_age: number; max_age: number }[] };
export type RatingsResponse = { items: AthleteRating[]; page: number; page_size: number; total: number; pages: number };
export type TeamMembership = { id: number; athlete: number; athlete_name: string; athlete_email: string; position: number; selected_by: number; selected_at: string; removed_at: string | null; removal_reason: string; eligibility_snapshot: { eligible: boolean; age: number | null; consent: boolean; guardian_verified: boolean; restriction: string | null; rating_score: string | null }; current_eligibility?: { eligible: boolean; restriction: string | null }; selection_note: string };
export type RegionalTeam = { id: number; name: string; region: string; status: "draft" | "published"; season: number; season_year: number; discipline: number; discipline_code: string; discipline_name: string; age_group: number; age_group_name: string; created_by: number; created_at: string; updated_at: string; member_count: number; members: TeamMembership[] };
export type TeamCandidate = { id: number; full_name: string; email: string; sport_rank?: string | null; eligible: boolean; selected: boolean; eligibility: { age: number | null; consent: boolean; guardian_verified: boolean; restriction: string | null; rating_score: string | null }; rating: { score: string; base_score: string; prize_count: number; position?: number } | null };
export type TeamOptions = { seasons: { id: number; year: number; name: string }[]; disciplines: Discipline[]; age_groups: AgeGroup[] };

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); }
}

async function csrfToken(signal?: AbortSignal | null): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf/", { credentials: "include", signal });
  if (!response.ok) throw new Error("Не удалось подготовить запрос");
  const data = await response.json();
  return data.csrfToken;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const unsafe = init?.method && !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase());
  const token = unsafe ? await csrfToken(init?.signal) : undefined;
  const response = await fetch(`/api/v1/${path}`, {
    credentials: "include",
    ...init,
    headers: { "Content-Type": "application/json", ...(token ? { "X-CSRFToken": token } : {}), ...init?.headers },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(typeof error.detail === "string" ? error.detail : JSON.stringify(error), response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export async function downloadDocument(path: string): Promise<Blob> {
  const response = await fetch(`/api/v1/${path}`, { credentials: "include" });
  if (!response.ok) throw new ApiError("Не удалось скачать документ", response.status);
  return response.blob();
}
