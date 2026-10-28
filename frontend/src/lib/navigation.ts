import type { Me, Role } from "@/lib/api";

const pageRoles: Record<string, readonly Role[]> = {
  "/dashboard": ["federation", "athlete", "coach", "judge"],
  "/qualifications": ["federation", "athlete", "coach", "judge"],
  "/teams": ["federation"],
  "/registry": ["federation"],
  "/analytics": ["federation"],
  "/history": ["athlete"],
  "/coach-links": ["athlete", "coach"],
  "/my-competitions": ["athlete", "coach", "judge"],
};

/** Presentation only; API authorization remains the source of truth. */
export function canAccessPage(href: string, user: Me | null): boolean {
  const path = href.split(/[?#]/)[0];
  const rule = Object.entries(pageRoles).find(([prefix]) => path === prefix || path.startsWith(`${prefix}/`));
  if (!rule) return true;
  const role = user?.active_role;
  return !!role && user.roles.includes(role) && rule[1].includes(role);
}

export const navigation = [
  { href: "/", label: "Главная", number: "01", icon: "home", mobile: true },
  { href: "/#disciplines", label: "Дисциплины", number: "02", icon: "users", mobile: true },
  { href: "/competitions", label: "Календарь", number: "03", icon: "cal", mobile: true },
  { href: "/dashboard", label: "Кабинет", number: "04", icon: "dots", mobile: true },
  { href: "/ratings", label: "Рейтинги", number: "05", icon: "dots", mobile: false },
  { href: "/teams", label: "Команды", number: "06", icon: "dots", mobile: true },
  { href: "/registry", label: "Реестры", number: "07", icon: "users", mobile: false },
  { href: "/analytics/participation", label: "Аналитика", number: "08", icon: "dots", mobile: false },
] as const;
