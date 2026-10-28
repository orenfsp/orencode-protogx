import Link from "next/link";
import { FeatureWorkspace } from "@/components/FeatureWorkspace";
export default function NewcomerPage() {
  return <><FeatureWorkspace title="Начать заниматься" endpoint="newcomer/" publicAccess columns={[{key:"kind",label:"Раздел"},{key:"name",label:"Название"},{key:"description",label:"Как начать"}]}/><section className="blk"><h2><b>02</b><span>Первые шаги</span></h2><div><p>Выберите дисциплину и организацию. Ознакомьтесь с регламентом, возрастной группой и сроком регистрации. Для несовершеннолетних потребуется проверенное согласие законного представителя.</p><div className="cta"><Link className="btn p" href="/register">Регистрация</Link><Link className="btn" href="/competitions">Календарь</Link><Link className="btn" href="/glossary">Понятия и руководства</Link></div></div></section></>;
}
