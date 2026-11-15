import { FetchSessionApi } from "./session-api.js";
import { withCsrfHeader } from "./csrf.js";

type Profile = { profile_id: string; name: string; permissions: string[]; active: boolean; revision: number };
type OBSNode = { obs_id: string; parent_obs_id: string | null; code: string; name: string; manager_user_id: string | null; sequence_number: number };
type Assignment = { user_id: string; obs_id: string; profile_id: string; active: boolean; revision: number; assigned_by: string; assigned_at: string };
type Privilege = { key: string; group: string; label: string; description: string };
type Locale = "en" | "fa";
const VERSION = "cubi-enterprise-project-access.v1";
const COPY = {
  en: {
    title:"Project Access", subtitle:"Manage OBS responsibility, project security profiles and user assignments.",
    back:"Organization & Access", refresh:"Refresh", profiles:"Project security profiles", createProfile:"Create profile",
    profileId:"Profile ID", profileName:"Profile name", permissions:"Project permissions", read:"Read", write:"Write",
    schedule:"Schedule", admin:"Project administration", create:"Create", obs:"Organizational breakdown structure",
    assignments:"User OBS assignments", userId:"User ID", obsNode:"OBS element", profile:"Security profile",
    assign:"Assign OBS", load:"Load assignments", revoke:"Revoke", noProfiles:"No active profiles.",
    noOBS:"No OBS elements are available.", noAssignments:"No active assignments for this user.",
    required:"Complete all required fields.", created:"Security profile created.", assigned:"OBS access assigned.",
    revoked:"OBS access revoked.", failed:"The request could not be completed.", session:"Your session has expired. Sign in again.",
    adminOnly:"Enterprise administrator access is required.", rootWarning:"Assigning the root OBS grants access to every project beneath it.",
    select:"Select…", manager:"Responsible manager", status:"Status", active:"Active", inactive:"Revoked",
  },
  fa: {
    title:"دسترسی پروژه", subtitle:"مدیریت مسئولیت OBS، پروفایل‌های امنیتی پروژه و تخصیص کاربران.",
    back:"سازمان و دسترسی", refresh:"تازه‌سازی", profiles:"پروفایل‌های امنیتی پروژه", createProfile:"ایجاد پروفایل",
    profileId:"شناسه پروفایل", profileName:"نام پروفایل", permissions:"مجوزهای پروژه", read:"خواندن", write:"ویرایش",
    schedule:"زمان‌بندی", admin:"مدیریت پروژه", create:"ایجاد", obs:"ساختار شکست سازمانی",
    assignments:"تخصیص‌های OBS کاربران", userId:"شناسه کاربر", obsNode:"عنصر OBS", profile:"پروفایل امنیتی",
    assign:"تخصیص OBS", load:"بارگذاری تخصیص‌ها", revoke:"لغو دسترسی", noProfiles:"پروفایل فعالی وجود ندارد.",
    noOBS:"عنصر OBS در دسترس نیست.", noAssignments:"تخصیص فعالی برای این کاربر وجود ندارد.",
    required:"تمام فیلدهای ضروری را تکمیل کنید.", created:"پروفایل امنیتی ایجاد شد.", assigned:"دسترسی OBS تخصیص یافت.",
    revoked:"دسترسی OBS لغو شد.", failed:"انجام درخواست ممکن نشد.", session:"نشست شما پایان یافته است؛ دوباره وارد شوید.",
    adminOnly:"دسترسی مدیر سازمانی لازم است.", rootWarning:"تخصیص OBS ریشه، دسترسی به تمام پروژه‌های زیرمجموعه را ایجاد می‌کند.",
    select:"انتخاب…", manager:"مسئول", status:"وضعیت", active:"فعال", inactive:"لغوشده",
  },
} as const;

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", value = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value) node.textContent = value;
  return node;
}
function button(label: string, secondary = false): HTMLButtonElement {
  const node = el("button", secondary ? "ce-button ce-button-secondary" : "ce-button ce-button-primary", label);
  node.type = "button";
  return node;
}
async function api<T>(path: string, method = "GET", payload?: unknown): Promise<T> {
  const headers: Record<string,string> = { Accept:"application/json" };
  if (payload !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { method, credentials:"same-origin", headers:withCsrfHeader(method,headers),
    body:payload === undefined ? undefined : JSON.stringify(payload), cache:"no-store" });
  const data: unknown = await response.json().catch(() => ({}));
  if (response.status === 401) throw new Error("SESSION_REQUIRED");
  if (!response.ok) throw new Error(typeof data === "object" && data !== null && "code" in data ? String((data as {code:unknown}).code) : "REQUEST_FAILED");
  return data as T;
}

export async function mountEnterpriseProjectAccess(container: HTMLElement): Promise<void> {
  const locale: Locale = navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
  const t = COPY[locale];
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
  document.title = `CUBI Enterprise · ${t.title}`;
  const session = await new FetchSessionApi(window.location.origin).getSession();
  if (!session.ok) { window.location.assign(`/login?next=${encodeURIComponent("/enterprise/project-access")}`); return; }
  if (!session.data.roles.includes("enterprise_admin")) {
    container.replaceChildren(el("main","ce-shell",t.adminOnly)); return;
  }

  const shell = el("main","ce-shell oa-shell");
  shell.dir = locale === "fa" ? "rtl" : "ltr";
  const header = el("header","ce-header");
  const brand = el("a","ce-brand","CUBI"); brand.href="/app";
  const back = el("a","ce-back",`← ${t.back}`); back.href="/enterprise/organization";
  header.append(brand,el("strong","",t.title),back);
  const hero = el("section","ce-hero");
  const heroCopy = el("div"); heroCopy.append(el("p","ce-eyebrow","CUBI ENTERPRISE"),el("h1","",t.title),el("p","ce-subtitle",t.subtitle));
  const refresh = button(t.refresh,true); hero.append(heroCopy,refresh);
  const status = el("p","ce-notice"); status.hidden=true; status.setAttribute("role","status");
  const error = el("p","ce-error"); error.hidden=true; error.setAttribute("role","alert");
  const grid = el("div","oa-grid");

  const profileCard = el("section","oa-card"); profileCard.append(el("h2","",t.profiles));
  const profileList = el("div","oa-list"); profileCard.append(profileList);
  const profileForm = el("form","oa-form");
  const profileId = el("input","ce-search") as HTMLInputElement; profileId.required=true; profileId.maxLength=120; profileId.placeholder=t.profileId;
  const profileName = el("input","ce-search") as HTMLInputElement; profileName.required=true; profileName.maxLength=160; profileName.placeholder=t.profileName;
  const permissionWrap = el("div","oa-list");
  const permissionInputs: HTMLInputElement[]=[];
  const legacyDefinitions: Privilege[]=[
    {key:"project.read",group:"legacy",label:locale==="fa"?"خواندن پروژه (سازگاری)":"Project read (compatibility)",description:"Legacy compatibility grant."},
    {key:"project.write",group:"legacy",label:locale==="fa"?"ویرایش پروژه (سازگاری)":"Project write (compatibility)",description:"Legacy compatibility grant."},
    {key:"project.schedule",group:"legacy",label:locale==="fa"?"زمان‌بندی (سازگاری)":"Project schedule (compatibility)",description:"Legacy compatibility grant."},
    {key:"project.admin",group:"legacy",label:locale==="fa"?"مدیریت پروژه (سازگاری)":"Project administration (compatibility)",description:"Legacy compatibility grant."},
  ];
  const createProfile=button(t.createProfile); createProfile.type="submit";
  profileForm.append(profileId,profileName,el("h3","",t.permissions),permissionWrap,createProfile);
  profileCard.append(profileForm);

  const obsCard=el("section","oa-card"); obsCard.append(el("h2","",t.obs));
  const obsList=el("div","oa-list"); obsCard.append(obsList);

  const accessCard=el("section","oa-card"); accessCard.append(el("h2","",t.assignments));
  const assignmentForm=el("form","oa-form");
  const userId=el("input","ce-search") as HTMLInputElement; userId.required=true; userId.placeholder=t.userId;
  const obsSelect=el("select","ce-select") as HTMLSelectElement; obsSelect.required=true;
  const profileSelect=el("select","ce-select") as HTMLSelectElement; profileSelect.required=true;
  const assignButton=button(t.assign); assignButton.type="submit";
  const loadButton=button(t.load,true);
  assignmentForm.append(userId,obsSelect,profileSelect,assignButton,loadButton);
  const rootWarning=el("p","oa-muted",t.rootWarning); rootWarning.hidden=true;
  const assignmentList=el("div","oa-list");
  accessCard.append(assignmentForm,rootWarning,assignmentList);
  grid.append(profileCard,obsCard);
  shell.append(header,hero,status,error,grid,accessCard);
  container.replaceChildren(shell);

  let profiles: Profile[]=[];
  let nodes: OBSNode[]=[];
  const notify=(text:string)=>{status.textContent=text;status.hidden=false;error.hidden=true;};
  const fail=(reason:unknown)=>{error.textContent=reason instanceof Error && reason.message==="SESSION_REQUIRED"?t.session:t.failed;error.hidden=false;status.hidden=true;};
  const loadAssignments=async()=>{
    const id=userId.value.trim(); if(!id){fail(new Error("REQUIRED"));return;}
    try{
      const result=await api<{assignments:Assignment[]}>(`/api/enterprise/user-obs-access/${encodeURIComponent(id)}`);
      assignmentList.replaceChildren();
      const active=result.assignments.filter(item=>item.active);
      if(!active.length){assignmentList.append(el("p","oa-muted",t.noAssignments));return;}
      for(const item of active){
        const node=nodes.find(value=>value.obs_id===item.obs_id);
        const profile=profiles.find(value=>value.profile_id===item.profile_id);
        const row=el("article","oa-row");
        const detail=el("div");
        detail.append(el("strong","",node?(`${node.code} · ${node.name}`):item.obs_id),el("small","",profile?.name??item.profile_id));
        const revoke=button(t.revoke,true);
        revoke.addEventListener("click",async()=>{try{
          await api(`/api/enterprise/user-obs-access/${encodeURIComponent(item.user_id)}/${encodeURIComponent(item.obs_id)}`,"DELETE",
            {contract_version:VERSION,profile_id:item.profile_id,expected_revision:item.revision});
          notify(t.revoked);await loadAssignments();
        }catch(reason){fail(reason);}});
        row.append(detail,revoke);assignmentList.append(row);
      }
    }catch(reason){fail(reason);}
  };
  const load=async()=>{
    const [p,o,g]=await Promise.all([
      api<{profiles:Profile[]}>(`/api/enterprise/project-security-profiles`),
      api<{obs_nodes:OBSNode[]}>(`/api/enterprise/obs`),
      api<{privileges:Privilege[]}>(`/api/enterprise/project-security-privileges`),
    ]);
    profiles=p.profiles;nodes=o.obs_nodes;
    permissionWrap.replaceChildren();permissionInputs.length=0;
    const grouped=new Map<string,Privilege[]>();
    for(const item of [...legacyDefinitions,...g.privileges]){
      const bucket=grouped.get(item.group)??[];bucket.push(item);grouped.set(item.group,bucket);
    }
    for(const [group,items] of grouped){
      const section=el("section","oa-privilege-group");
      section.append(el("h3","",group.replaceAll("_"," ").toUpperCase()));
      const actions=el("div","oa-inline");
      const selectAll=button(locale==="fa"?"انتخاب همه":"Select all",true);
      const clearAll=button(locale==="fa"?"پاک‌کردن":"Clear",true);
      const groupInputs:HTMLInputElement[]=[];
      actions.append(selectAll,clearAll);section.append(actions);
      const choices=el("div","oa-inline");
      for(const item of items){
        const labelNode=el("label","oa-inline");const input=el("input") as HTMLInputElement;
        input.type="checkbox";input.value=item.key;input.checked=item.key==="project.read";
        groupInputs.push(input);permissionInputs.push(input);
        labelNode.append(input,el("span","",item.label));choices.append(labelNode);
      }
      selectAll.addEventListener("click",()=>groupInputs.forEach(input=>input.checked=true));
      clearAll.addEventListener("click",()=>groupInputs.forEach(input=>input.checked=false));
      section.append(choices);permissionWrap.append(section);
    }
    profileList.replaceChildren();profileSelect.replaceChildren();
    for(const item of profiles.filter(value=>value.active)){
      const row=el("article","oa-row");
      row.append(el("div","",`${item.name} · ${item.profile_id}`),el("small","oa-muted",item.permissions.join(", ")));
      profileList.append(row);
      const option=el("option","",item.name) as HTMLOptionElement;option.value=item.profile_id;profileSelect.append(option);
    }
    if(!profiles.length)profileList.append(el("p","oa-muted",t.noProfiles));
    obsList.replaceChildren();obsSelect.replaceChildren();
    const placeholder=el("option","",t.select) as HTMLOptionElement;placeholder.value="";placeholder.disabled=true;placeholder.selected=true;obsSelect.append(placeholder);
    const byParent=new Map<string|null,OBSNode[]>();
    for(const node of nodes){const key=node.parent_obs_id;const bucket=byParent.get(key)??[];bucket.push(node);byParent.set(key,bucket);}
    const append=(parent:string|null,depth:number)=>{
      for(const node of (byParent.get(parent)??[]).sort((a,b)=>a.sequence_number-b.sequence_number)){
        const prefix="— ".repeat(depth);
        const option=el("option","",`${prefix}${node.code} · ${node.name}`) as HTMLOptionElement;option.value=node.obs_id;obsSelect.append(option);
        const row=el("article","oa-row");row.append(el("div","",`${prefix}${node.code} · ${node.name}`),el("small","oa-muted",node.manager_user_id??""));
        obsList.append(row);append(node.obs_id,depth+1);
      }
    };
    append(null,0);
    if(!nodes.length)obsList.append(el("p","oa-muted",t.noOBS));
  };
  profileForm.addEventListener("submit",async event=>{
    event.preventDefault();
    const permissions=permissionInputs.filter(input=>input.checked).map(input=>input.value);
    if(!profileId.value.trim()||!profileName.value.trim()||!permissions.length){fail(new Error("REQUIRED"));return;}
    try{
      await api("/api/enterprise/project-security-profiles","POST",{contract_version:VERSION,profile_id:profileId.value.trim(),name:profileName.value.trim(),permissions});
      profileId.value="";profileName.value="";notify(t.created);await load();
    }catch(reason){fail(reason);}
  });
  assignmentForm.addEventListener("submit",async event=>{
    event.preventDefault();
    if(!userId.value.trim()||!obsSelect.value||!profileSelect.value){fail(new Error("REQUIRED"));return;}
    try{
      await api("/api/enterprise/user-obs-access","POST",{contract_version:VERSION,user_id:userId.value.trim(),obs_id:obsSelect.value,profile_id:profileSelect.value});
      rootWarning.hidden=nodes.find(node=>node.obs_id===obsSelect.value)?.parent_obs_id!==null;
      notify(t.assigned);await loadAssignments();
    }catch(reason){fail(reason);}
  });
  loadButton.addEventListener("click",()=>void loadAssignments());
  refresh.addEventListener("click",()=>void load().then(loadAssignments).catch(fail));
  obsSelect.addEventListener("change",()=>{rootWarning.hidden=nodes.find(node=>node.obs_id===obsSelect.value)?.parent_obs_id!==null;});
  try{await load();}catch(reason){fail(reason);}
}
