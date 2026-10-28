import { FeatureWorkspace } from "@/components/FeatureWorkspace";
export default function MinistryPage() { return <FeatureWorkspace title="Кабинет министерства" endpoint="ministry/" columns={[{key:"kind",label:"Раздел"},{key:"name",label:"Название"},{key:"details",label:"Сведения"},{key:"source",label:"Источник"}]}/>; }
