"use client";
import { useState } from "react";
import { FeatureWorkspace, WorkspaceProps } from "@/components/FeatureWorkspace";
export function ReportFilters({ mode, ...props }: WorkspaceProps & { mode: "years" | "year" | "newcomer" }) {
  const [query,setQuery]=useState("");
  const year=new Date().getFullYear();
  return <><form className="workflow-form" aria-label="Фильтры отчёта" onSubmit={event=>{event.preventDefault();const values=new FormData(event.currentTarget);const params=new URLSearchParams();for(const [key,value]of values)if(value)params.set(key,String(value));setQuery(params.toString());}}>
    {mode==="newcomer"?<label>Муниципалитет<input className="inp" name="municipality" maxLength={200}/></label>:<>
      {mode==="years"&&<label>Начальный год<input className="inp" name="start_year" type="number" min="1900" max="2199" defaultValue={year-1} required/></label>}
      <label>{mode==="years"?"Последний год":"Год"}<input className="inp" name={mode==="years"?"end_year":"year"} type="number" min="1901" max="2200" defaultValue={year} required/></label>
    </>}
    <button className="btn">Применить фильтры</button>
  </form><FeatureWorkspace {...props} endpoint={props.endpoint+(query?`?${query}`:"")}/>{mode==="years"&&<a className="btn" href={`/api/v1/${props.endpoint}?${query?query+"&":""}file_format=xlsx`}>Скачать XLSX</a>}</>;
}
