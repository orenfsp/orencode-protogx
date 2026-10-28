import { FeatureWorkspace } from "@/components/FeatureWorkspace";
export default function AwardsPage(){return <FeatureWorkspace title="Премии Губернатора" endpoint="awards/" columns={[{key:"id",label:"№"},{key:"kind",label:"Вид"},{key:"name",label:"Кандидат / ходатайство"},{key:"amount",label:"Сумма (демо)"},{key:"status",label:"Статус"},{key:"details",label:"Основание"}]} actions={[
 {label:"Проверить список и подготовить пакет",path:"awards/prepare/",roles:["federation"],fields:[{name:"scheme",label:"Версия справочника",options:"schemes"}]},
 {label:"Записать демонстрационный статус",path:"awards/{id}/action/",roles:["federation"],fields:[{name:"id",label:"Ходатайство",options:"petitions"},{name:"expected_revision",label:"Текущая ревизия",type:"number"},{name:"status",label:"Статус",choices:[{value:"sent",label:"Направлено (демонстрация)"},{value:"awarded",label:"Назначено (демонстрация)"}]},{name:"reason",label:"Основание проверки"}]}
 ]}/>;}
