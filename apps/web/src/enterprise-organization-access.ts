import { FetchSessionApi } from "./session-api.js";
import { withCsrfHeader } from "./csrf.js";

type Team = { team_id: string; name: string; owner_user_id: string; status: string; revision: number };
type Membership = { team_id: string; user_id: string; role: string; status: string; revision: number; scope_project_ids: string[] };
type Invitation = { invitation_id: string; team_id: string; role: string; status: string; expires_at: string; created_at: string };
type Identity = { cubi_id: string; display_name: string };
type Locale = "en" | "fa";

const COPY = {
  en: {
    title:"Organization & Access", subtitle:"Manage teams, invitations, membership and ownership.",
    back:"Task Center", refresh:"Refresh", myId:"My CUBI ID", copy:"Copy ID",
    teams:"Teams", createTeam:"Create team", teamName:"Team name", create:"Create",
    members:"Team members", inbox:"Received invitations", invite:"Invite by CUBI ID",
    cubiId:"CUBI ID", lookup:"Find user", role:"Team role", send:"Send invitation",
    owner:"Owner", admin:"Admin", project_manager:"Project manager", approver:"Approver",
    field_worker:"Field worker", member:"Member", viewer:"Viewer",
    transfer:"Transfer ownership", remove:"Remove", accept:"Accept", decline:"Decline",
    noTeams:"No teams yet.", noMembers:"No members.", noInvites:"No pending invitations.",
    session:"Your session has expired. Sign in again.", failed:"The request could not be completed.",
    created:"Team created.", invited:"Invitation sent. The recipient can accept it from their inbox.",
    transferred:"Team ownership transferred.", removed:"Member removed.", accepted:"Invitation accepted.",
    declined:"Invitation declined.", copied:"CUBI ID copied.", lookupFound:"Found",
    expiry:"Expires", selectTeam:"Select a team", confirmTransfer:"Transfer team ownership to this active member?",
    confirmRemove:"Remove this team member?", entitlement:"Team creation requires an active Pro entitlement and enterprise administrator access.", noManager:"You do not have permission to manage this team.",
  },
  fa: {
    title:"سازمان و دسترسی", subtitle:"مدیریت تیم‌ها، دعوت‌ها، عضویت‌ها و مالکیت.",
    back:"مرکز وظایف", refresh:"تازه‌سازی", myId:"شناسه CUBI من", copy:"کپی شناسه",
    teams:"تیم‌ها", createTeam:"ایجاد تیم", teamName:"نام تیم", create:"ایجاد",
    members:"اعضای تیم", inbox:"دعوت‌های دریافتی", invite:"دعوت با شناسه CUBI",
    cubiId:"شناسه CUBI", lookup:"یافتن کاربر", role:"نقش تیم", send:"ارسال دعوت",
    owner:"مالک", admin:"مدیر", project_manager:"مدیر پروژه", approver:"تأییدکننده",
    field_worker:"کاربر کارگاهی", member:"عضو", viewer:"مشاهده‌گر",
    transfer:"انتقال مالکیت", remove:"حذف", accept:"پذیرش", decline:"رد",
    noTeams:"هنوز تیمی وجود ندارد.", noMembers:"عضوی وجود ندارد.", noInvites:"دعوت معلقی وجود ندارد.",
    session:"نشست شما پایان یافته است؛ دوباره وارد شوید.", failed:"انجام درخواست ممکن نشد.",
    created:"تیم ایجاد شد.", invited:"دعوت ارسال شد؛ گیرنده می‌تواند آن را از صندوق دعوت‌ها بپذیرد.",
    transferred:"مالکیت تیم منتقل شد.", removed:"عضو حذف شد.", accepted:"دعوت پذیرفته شد.",
    declined:"دعوت رد شد.", copied:"شناسه CUBI کپی شد.", lookupFound:"یافت شد",
    expiry:"انقضا", selectTeam:"انتخاب تیم", confirmTransfer:"مالکیت تیم به این عضو فعال منتقل شود؟",
    confirmRemove:"این عضو از تیم حذف شود؟", entitlement:"ایجاد تیم به اشتراک فعال Pro و دسترسی مدیر سازمان نیاز دارد.", noManager:"مجوز مدیریت این تیم را ندارید.",
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
  const response = await fetch(path, {
    method, credentials:"same-origin",
    headers: withCsrfHeader(method, headers),
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  const data: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const code = typeof data === "object" && data !== null && "code" in data ? String((data as {code:unknown}).code) : "REQUEST_FAILED";
    throw new Error(code);
  }
  return data as T;
}
function message(node: HTMLElement, value: string): void { node.textContent = value; node.hidden = false; }

export async function mountEnterpriseOrganizationAccess(container: HTMLElement): Promise<void> {
  const locale: Locale = navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
  const t = COPY[locale];
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
  document.title = `CUBI Enterprise · ${t.title}`;
  container.replaceChildren();

  const shell = el("main","ce-shell oa-shell");
  shell.dir = locale === "fa" ? "rtl" : "ltr";
  const header = el("header","ce-header");
  const brand = el("a","ce-brand","CUBI"); brand.href="/app";
  const back = el("a","ce-back",`← ${t.back}`); back.href="/enterprise";
  header.append(brand,el("strong","",t.title),back);
  const hero = el("section","ce-hero");
  const copy = el("div"); copy.append(el("p","ce-eyebrow","CUBI ENTERPRISE"),el("h1","",t.title),el("p","ce-subtitle",t.subtitle));
  const refresh = button(t.refresh,true); hero.append(copy,refresh);
  const status = el("p","ce-notice"); status.hidden=true; status.setAttribute("role","status");
  const error = el("p","ce-error"); error.hidden=true; error.setAttribute("role","alert");

  const identityCard = el("section","oa-card");
  identityCard.append(el("h2","",t.myId));
  const idRow = el("div","oa-inline");
  const myId = el("strong","oa-cubi-id","—");
  const copyId = button(t.copy,true);
  idRow.append(myId,copyId); identityCard.append(idRow);

  const grid = el("div","oa-grid");
  const teamCard = el("section","oa-card");
  teamCard.append(el("h2","",t.teams));
  const teamSelect = el("select","ce-select") as HTMLSelectElement;
  teamSelect.setAttribute("aria-label",t.selectTeam);
  teamCard.append(teamSelect);
  const createForm = el("form","oa-inline") as HTMLFormElement;
  const teamName = el("input","ce-search") as HTMLInputElement; teamName.required=true; teamName.maxLength=200; teamName.placeholder=t.teamName;
  const createButton = button(t.create); createButton.type="submit";
  createForm.append(teamName,createButton); teamCard.append(createForm);

  const memberCard = el("section","oa-card");
  memberCard.append(el("h2","",t.members));
  const members = el("div","oa-list"); memberCard.append(members);
  const inviteForm = el("form","oa-form") as HTMLFormElement;
  inviteForm.append(el("h3","",t.invite));
  const cubiInput = el("input","ce-search") as HTMLInputElement; cubiInput.placeholder=t.cubiId; cubiInput.required=true;
  const lookup = button(t.lookup,true);
  const identityResult = el("p","oa-muted"); identityResult.hidden=true;
  const role = el("select","ce-select") as HTMLSelectElement;
  for (const value of ["member","field_worker","project_manager","approver","viewer","admin"]) {
    const option=el("option","",t[value as keyof typeof t] as string) as HTMLOptionElement; option.value=value; role.append(option);
  }
  const sendInvite = button(t.send); sendInvite.type="submit";
  inviteForm.append(cubiInput,lookup,identityResult,role,sendInvite); memberCard.append(inviteForm);
  const transferRow = el("div","oa-inline");
  const transferSelect = el("select","ce-select") as HTMLSelectElement;
  const transferButton = button(t.transfer,true);
  transferRow.append(transferSelect,transferButton); memberCard.append(transferRow);

  const inboxCard = el("section","oa-card");
  inboxCard.append(el("h2","",t.inbox));
  const inbox = el("div","oa-list"); inboxCard.append(inbox);
  grid.append(teamCard,memberCard);
  shell.append(header,hero,status,error,identityCard,grid,inboxCard);
  container.append(shell);

  let teams: Team[]=[];
  let selected: Team | null=null;
  let currentUserId="";
  let membersData: Membership[]=[];
  let foundIdentity: Identity | null=null;
  const showError=(reason: unknown):void=>{
    const code=reason instanceof Error ? reason.message : "";
    message(error,code==="SESSION_REQUIRED" ? t.session : t.failed); status.hidden=true;
  };
  const showStatus=(value:string):void=>{message(status,value);error.hidden=true;};
  const loadInbox=async():Promise<void>=>{
    const result=await api<{invitations:Invitation[]}>("/api/enterprise/invitations/inbox");
    inbox.replaceChildren();
    if(!result.invitations.length){inbox.append(el("p","oa-muted",t.noInvites));return;}
    for(const item of result.invitations){
      const row=el("article","oa-row");
      const details=el("div"); details.append(el("strong","",`${item.team_id} · ${t[item.role as keyof typeof t] ?? item.role}`),el("small","",`${t.expiry}: ${new Date(item.expires_at).toLocaleString(locale)}`));
      const actions=el("div","oa-inline");
      const accept=button(t.accept); const decline=button(t.decline,true);
      accept.addEventListener("click",async()=>{try{await api(`/api/enterprise/invitations/${encodeURIComponent(item.invitation_id)}/accept-from-inbox`,"POST",{});showStatus(t.accepted);await loadAll();}catch(e){showError(e);}});
      decline.addEventListener("click",async()=>{try{await api(`/api/enterprise/invitations/${encodeURIComponent(item.invitation_id)}/decline-from-inbox`,"POST",{});showStatus(t.declined);await loadInbox();}catch(e){showError(e);}});
      actions.append(accept,decline); row.append(details,actions); inbox.append(row);
    }
  };
  const loadMembers=async():Promise<void>=>{
    if(!selected){members.replaceChildren(el("p","oa-muted",t.noTeams));transferSelect.replaceChildren();inviteForm.hidden=true;transferRow.hidden=true;return;}
    let result: {memberships:Membership[]};
    try {
      result=await api<{memberships:Membership[]}>(`/api/enterprise/teams/${encodeURIComponent(selected.team_id)}/members`);
    } catch {
      members.replaceChildren(el("p","oa-muted",t.noManager));
      inviteForm.hidden=true; transferRow.hidden=true;
      return;
    }
    membersData=result.memberships; members.replaceChildren(); transferSelect.replaceChildren();
    const current=membersData.find(item=>item.user_id===currentUserId);
    const canManage=Boolean(current && current.status==="active" && (current.role==="owner" || current.role==="admin"));
    inviteForm.hidden=!canManage;
    const adminOption=Array.from(role.options).find(option=>option.value==="admin");
    if(adminOption) adminOption.disabled=current?.role!=="owner";
    for(const member of membersData){
      const row=el("article","oa-row");
      const info=el("div"); info.append(el("strong","",member.user_id),el("small","",`${t[member.role as keyof typeof t] ?? member.role} · ${member.status}`));
      row.append(info);
      if(member.user_id!==selected.owner_user_id && member.status==="active"){
        const remove=button(t.remove,true);
        remove.addEventListener("click",async()=>{if(!window.confirm(t.confirmRemove))return;try{await api(`/api/enterprise/teams/${encodeURIComponent(selected!.team_id)}/members/${encodeURIComponent(member.user_id)}`,"DELETE",{contract_version:"cubi-enterprise-organization-access.v1",expected_revision:member.revision});showStatus(t.removed);await loadMembers();}catch(e){showError(e);}});
        row.append(remove);
      }
      members.append(row);
      if(member.user_id!==currentUserId && member.status==="active"){
        const option=el("option","",member.user_id) as HTMLOptionElement; option.value=member.user_id; transferSelect.append(option);
      }
    }
    const canTransfer=selected.owner_user_id===currentUserId && Boolean(current);
    transferRow.hidden=!canTransfer || transferSelect.options.length===0;
  };
  const loadTeams=async():Promise<void>=>{
    const result=await api<{teams:Team[]}>("/api/enterprise/teams");
    teams=result.teams; teamSelect.replaceChildren();
    for(const team of teams){const option=el("option","",team.name) as HTMLOptionElement;option.value=team.team_id;teamSelect.append(option);}
    selected=teams.find(item=>item.team_id===teamSelect.value) ?? teams[0] ?? null;
    if(selected)teamSelect.value=selected.team_id;
    await loadMembers();
  };
  const loadAll=async():Promise<void>=>{await loadTeams();await loadInbox();};
  cubiInput.addEventListener("input",()=>{foundIdentity=null;identityResult.hidden=true;});
  lookup.addEventListener("click",async()=>{foundIdentity=null;identityResult.hidden=true;try{const result=await api<{identity:Identity}>(`/api/enterprise/cubi-id?value=${encodeURIComponent(cubiInput.value)}`);foundIdentity=result.identity;identityResult.textContent=`${t.lookupFound}: ${foundIdentity.display_name} · ${foundIdentity.cubi_id}`;identityResult.hidden=false;}catch(e){showError(e);}});
  createForm.addEventListener("submit",async(event)=>{event.preventDefault();try{await api("/api/enterprise/teams","POST",{contract_version:"cubi-enterprise-organization-access.v1",name:teamName.value.trim()});teamName.value="";showStatus(t.created);await loadTeams();}catch(e){showError(e);}});
  inviteForm.addEventListener("submit",async(event)=>{event.preventDefault();if(!foundIdentity){showError(new Error("LOOKUP_REQUIRED"));return;}try{await api(`/api/enterprise/teams/${encodeURIComponent(selected?.team_id ?? "")}/invitations`,"POST",{contract_version:"cubi-team-invitation.v1",cubi_id:foundIdentity.cubi_id,role:role.value});cubiInput.value="";foundIdentity=null;identityResult.hidden=true;showStatus(t.invited);}catch(e){showError(e);}});
  teamSelect.addEventListener("change",async()=>{selected=teams.find(item=>item.team_id===teamSelect.value)??null;try{await loadMembers();}catch(e){showError(e);}});
  transferButton.addEventListener("click",async()=>{if(!selected||!transferSelect.value||!window.confirm(t.confirmTransfer))return;try{await api(`/api/enterprise/teams/${encodeURIComponent(selected.team_id)}/transfer-ownership`,"POST",{contract_version:"cubi-enterprise-organization-access.v1",new_owner_user_id:transferSelect.value,expected_team_revision:selected.revision});showStatus(t.transferred);await loadTeams();}catch(e){showError(e);}});
  copyId.addEventListener("click",async()=>{try{await navigator.clipboard.writeText(myId.textContent??"");showStatus(t.copied);}catch(e){showError(e);}});
  refresh.addEventListener("click",()=>{void loadAll().catch(showError);});

  try{
    const session=await new FetchSessionApi(window.location.origin).getSession();
    if(!session.ok){window.location.assign(`/login?next=${encodeURIComponent("/enterprise/organization")}`);return;}
    currentUserId=session.data.user_id;
    const roles=new Set(session.data.roles);
    createForm.hidden=!(roles.has("enterprise_admin") && roles.has("pro_monthly_active"));
    const identity=await api<{cubi_id:string}>("/api/enterprise/cubi-id/me");
    myId.textContent=identity.cubi_id;
    await loadAll();
  }catch(reason){showError(reason);}
}
