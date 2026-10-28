import { FeatureWorkspace } from "@/components/FeatureWorkspace";
export default function CertificatesPage() {
  return <FeatureWorkspace title="Справки об участии" endpoint="certificates/" columns={[{key:"number",label:"Номер"},{key:"competition",label:"Соревнование"},{key:"status",label:"Статус"}]} actions={[
    {label:"Сформировать справку",path:"certificates/",fields:[{name:"application",label:"Участие",options:"applications"},{name:"public_name",label:"Показывать моё ФИО при публичной проверке (только совершеннолетние)",type:"checkbox"}]},
    {label:"Отозвать справку",path:"certificates/{id}/revoke/",fields:[{name:"id",label:"Справка для отзыва",options:"certificates"}]},
  ]}/>;
}
