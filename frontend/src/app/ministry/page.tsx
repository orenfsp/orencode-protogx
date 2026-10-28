import { ReportFilters } from "@/components/ReportFilters";
export default function MinistryPage() {
  return <ReportFilters mode="year" title="Кабинет министерства" endpoint="ministry/" columns={[{key:"kind",label:"Раздел"},{key:"name",label:"Название"},{key:"details",label:"Сведения"},{key:"source",label:"Источник"}]}/>;
}
