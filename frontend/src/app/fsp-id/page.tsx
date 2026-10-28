"use client";
import { useCurrentUser } from "@/components/AppShell";
import { FeatureWorkspace, Field } from "@/components/FeatureWorkspace";
const clientFields: Field[] = [
  {name:"name",label:"Название приложения"},
  {name:"client_type",label:"Тип клиента",choices:[{value:"public",label:"Публичный (PKCE)"},{value:"confidential",label:"Конфиденциальный (секрет + PKCE)"}]},
  {name:"redirect_uris",label:"Точный callback URI",type:"url",array:true},
  {name:"post_logout_redirect_uris",label:"Точный URI после выхода",type:"url",array:true,optional:true},
  {name:"scopes",label:"Разрешения приложения (openid обязателен)",array:true,choices:[{value:"openid",label:"Идентификатор"},{value:"profile",label:"ФИО"},{value:"fsp_roles",label:"Назначенные роли"},{value:"fsp_disciplines",label:"Дисциплины"},{value:"fsp_rank",label:"Действующие разряды"}]},
];
export default function FSPIDPage() {
  const me=useCurrentUser();
  return <><FeatureWorkspace title="ФСП ID: согласия" endpoint="fsp-id/consents/" columns={[{key:"id",label:"№"},{key:"name",label:"Приложение"},{key:"details",label:"Передаваемые сведения"},{key:"status",label:"Статус"}]} actions={[{label:"Отозвать согласие",path:"fsp-id/consents/{id}/revoke/",fields:[{name:"id",label:"Согласие",options:"consents"}]}]}/>
    {me?.active_role==="federation"&&<FeatureWorkspace title="Клиенты ФСП ID" endpoint="fsp-id/clients/" columns={[{key:"id",label:"№"},{key:"name",label:"Приложение"},{key:"client_id",label:"Client ID"},{key:"client_type",label:"Тип"},{key:"enabled",label:"Включён"},{key:"details",label:"Разрешения"}]} actions={[
      {label:"Зарегистрировать клиента",path:"fsp-id/clients/",roles:["federation"],fields:clientFields},
      {label:"Изменить клиента и отозвать прежние согласия",path:"fsp-id/clients/{id}/",method:"PUT",roles:["federation"],fields:[{name:"id",label:"Номер изменяемого клиента",type:"number"},...clientFields]},
      {label:"Сменить секрет клиента",path:"fsp-id/clients/{id}/rotate-secret/",roles:["federation"],fields:[{name:"id",label:"Номер конфиденциального клиента",type:"number"}]},
      {label:"Отключить клиента",path:"fsp-id/clients/{id}/disable/",roles:["federation"],fields:[{name:"id",label:"Номер отключаемого клиента",type:"number"}]},
    ]}/>}
    {me?.active_role==="federation"&&<FeatureWorkspace title="Согласия представителей для ФСП ID" endpoint="fsp-id/guardian-authorizations/" columns={[{key:"id",label:"№"},{key:"name",label:"Спортсмен"},{key:"application",label:"Приложение"},{key:"details",label:"Разрешения"},{key:"status",label:"Статус"}]} actions={[
      {label:"Зафиксировать проверенное согласие представителя (демо)",path:"fsp-id/guardian-authorizations/",roles:["federation"],fields:[{name:"guardian",label:"Проверенный представитель",options:"guardians"},{name:"application",label:"Клиентское приложение",options:"applications"},clientFields[4],{name:"text_version",label:"Версия текста отдельного согласия"},{name:"signed_evidence_url",label:"Приватная ссылка на подтверждение согласия",type:"url"}]},
      {label:"Отозвать разрешение представителя",path:"fsp-id/guardian-authorizations/{id}/revoke/",roles:["federation"],fields:[{name:"id",label:"Разрешение представителя",options:"authorizations"}]},
    ]}/>}
  </>;
}
