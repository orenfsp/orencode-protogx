"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

export type RegistryOptions = { organizations: { id: number; name: string }[]; disciplines: { id: number; name: string }[]; age_groups: { id: number; name: string }[]; municipalities: string[] };

export function useRegistryOptions() {
  const [options, setOptions] = useState<RegistryOptions | null>(null);
  const [optionsError, setOptionsError] = useState("");
  const [optionsForbidden, setOptionsForbidden] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    api<RegistryOptions>("registry/options/", { signal: controller.signal }).then((data) => { if (!controller.signal.aborted) setOptions(data); }).catch((error) => { if (!controller.signal.aborted) { if (error instanceof ApiError && (error.status === 401 || error.status === 403)) setOptionsForbidden(true); else setOptionsError(error instanceof Error ? error.message : "Не удалось загрузить справочники"); } });
    return () => controller.abort();
  }, []);
  return { options, optionsError, optionsForbidden };
}
