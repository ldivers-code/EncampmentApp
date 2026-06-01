"""All Pydantic models and data classes for the CAP Encampment application"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any


class UserRole:
    DCP = "dcp"
    COMMANDER = "commander"
    EXECUTIVE_STAFF = "executive_staff"
    LOGISTICS = "logistics"
    TRAINING_OFFICER = "training_officer"
    SUPERINTENDENT = "superintendent"
    CHIEF_TRAINING_OFFICER = "chief_training_officer"
    FINANCE = "finance"
    PLANS_PROGRAMS = "plans_programs"
    PUBLIC_AFFAIRS = "public_affairs"
    EXEC_CADRE = "exec_cadre"
    STAFF = "staff"
    CADRE = "cadre"
    STUDENT = "student"
    HEALTH_SERVICES = "health_services"
    DINING_FACILITY = "dining_facility"
    SUPPORT_LOGISTICS = "support_logistics"
    SUPPORT_COMMS = "support_comms"
    SUPPORT_PA = "support_pa"
    SUPPORT_DINING = "support_dining"
    SUPPORT_HEALTH = "support_health"
    SQUADRON_COMMANDER = "squadron_commander"
    PARENT = "parent"


class UserUnit:
    STAFF = "staff"
    SUPPORT_CADRE = "support_cadre"
    EXEC_CADRE = "exec_cadre"
    OPS_CADRE = "ops_cadre"


class ParticipantType:
    """Canonical participant classification (encampment-level).

    The single source of truth is the Registration Zone SubEvents column.
    Cadets are NEVER classified as Senior Staff — that is reserved for
    senior members. Exec Cadre is a SUBSET of Cadre (use the
    `is_exec_cadre` flag on the participant row) — NOT a separate type.
    """
    SENIOR_STAFF = "senior_staff"   # senior member + Senior Staff sub-event
    CADRE = "cadre"                  # cadet + Cadre sub-event
    STUDENT = "student"              # cadet + Student sub-event
    NEEDS_REVIEW = "needs_review"    # sub-event missing / ambiguous / mismatched


# Alias sets to absorb legacy values during the transition. These are READ-side
# only — new rows must use the canonical values above.
LEGACY_SENIOR_STAFF_ALIASES = {"senior_staff", "staff", "senior_member"}
LEGACY_CADRE_ALIASES = {"cadre", "exec_cadre"}
LEGACY_STUDENT_ALIASES = {"student", "basic_student", "advanced_student"}


class AccessPermissions(BaseModel):
    dashboard: bool = True
    roster_view: bool = True
    roster_edit: bool = False
    schedule_view: bool = True
    schedule_edit: bool = False
    meal_plan_view: bool = True
    meal_plan_edit: bool = False
    budget_view: bool = False
    budget_edit: bool = False
    analytics: bool = False
    org_chart: bool = True
    handbooks: bool = True
    documents: bool = True
    admin_panel: bool = False
    health_view: bool = False
    health_full: bool = False
    check_in_view: bool = False
    check_in_edit: bool = False
    page_health: bool = False
    page_check_in: bool = False
    page_barracks: bool = False
    page_logistics: bool = False
    page_meal_plan: bool = False
    page_training: bool = False
    page_status_board: bool = False
    page_parent_portal: bool = False


DEFAULT_PERMISSIONS = {
    UserRole.DCP: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        meal_plan_view=True, meal_plan_edit=True,
        budget_view=True, budget_edit=True,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=True,
        health_view=True, health_full=True,
        check_in_view=True, check_in_edit=True,
        page_parent_portal=True
    ),
    UserRole.COMMANDER: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        meal_plan_view=True, meal_plan_edit=True,
        budget_view=True, budget_edit=True,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=True,
        health_view=True, health_full=True,
        check_in_view=True, check_in_edit=True,
        page_parent_portal=True
    ),
    UserRole.EXECUTIVE_STAFF: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        meal_plan_view=True, meal_plan_edit=True,
        budget_view=True, budget_edit=True,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=True,
        health_view=True, health_full=True,
        check_in_view=True, check_in_edit=True,
        page_parent_portal=True
    ),
    UserRole.FINANCE: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=True, budget_edit=True,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.PLANS_PROGRAMS: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        meal_plan_view=True, meal_plan_edit=True,
        budget_view=False, budget_edit=False,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=True,
        health_view=False, health_full=False,
        check_in_view=True, check_in_edit=True
    ),
    # Phase 3: EXEC_CADRE is the cadre-lead permission role. It receives
    # ELEVATED CADRE-LEVEL permissions only — never Senior Staff capabilities
    # by default. `analytics` is a senior-staff cross-cutting view, so it is
    # OFF by default for cadre leads. Admin can grant it explicitly via the
    # per-user permission editor when warranted.
    UserRole.EXEC_CADRE: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.STAFF: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=True, health_full=False
    ),
    UserRole.CADRE: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.STUDENT: AccessPermissions(
        dashboard=True, roster_view=False, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.HEALTH_SERVICES: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=True, health_full=True
    ),
    UserRole.TRAINING_OFFICER: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=True, health_full=False
    ),
    UserRole.LOGISTICS: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False,
        check_in_view=True, check_in_edit=True
    ),
    UserRole.DINING_FACILITY: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=True,
        budget_view=False, budget_edit=False,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.SUPPORT_LOGISTICS: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False,
        check_in_view=True, check_in_edit=True
    ),
    UserRole.SUPPORT_COMMS: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.SUPPORT_PA: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.SUPPORT_DINING: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=True,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.SUPPORT_HEALTH: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=True, health_full=False
    ),
    UserRole.SQUADRON_COMMANDER: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        meal_plan_view=True, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=True, health_full=False,
        check_in_view=True, check_in_edit=True
    ),
    UserRole.PARENT: AccessPermissions(
        dashboard=False, roster_view=False, roster_edit=False,
        schedule_view=False, schedule_edit=False,
        meal_plan_view=False, meal_plan_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=False, handbooks=False,
        documents=False, admin_panel=False,
        health_view=False, health_full=False
    ),
}


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = UserRole.STAFF
    capid: str
    squadron: Optional[str] = None
    flight: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUnitAssignment(BaseModel):
    squadron: Optional[str] = None
    flight: Optional[str] = None
    support_section: Optional[str] = None
    cadre_unit: Optional[str] = None
    cadre_position: Optional[str] = None

class UserProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    cell_phone: Optional[str] = None
    capid: Optional[str] = None
    rank: Optional[str] = None
    unit: Optional[str] = None
    wing: Optional[str] = None
    region: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    shirt_size: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    cadet_parent_name: Optional[str] = None
    cadet_parent_phone: Optional[str] = None
    cadet_parent_email: Optional[str] = None
    photo_url: Optional[str] = None

class UserProfileUpdate(UserProfile):
    pass

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    capid: Optional[str] = None
    squadron: Optional[str] = None
    flight: Optional[str] = None
    created_at: str
    phone: Optional[str] = None
    cell_phone: Optional[str] = None
    rank: Optional[str] = None
    unit: Optional[str] = None
    wing: Optional[str] = None
    region: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    shirt_size: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    cadet_parent_name: Optional[str] = None
    cadet_parent_phone: Optional[str] = None
    cadet_parent_email: Optional[str] = None
    photo_url: Optional[str] = None
    is_approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    linked_participant_id: Optional[str] = None
    support_section: Optional[str] = None
    permissions: Optional[dict] = None
    honor_agreement_signed: Optional[bool] = None
    honor_agreement_type: Optional[str] = None
    honor_agreement_signed_at: Optional[str] = None
    cadre_unit: Optional[str] = None
    cadre_position: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ParticipantBase(BaseModel):
    capid: str
    rank: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    unit: str
    wing: Optional[str] = None
    region: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    age_at_event: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cell_phone: Optional[str] = None
    shirt_size: Optional[str] = None
    member_type: Optional[str] = None
    participant_type: str = ParticipantType.NEEDS_REVIEW
    is_exec_cadre: bool = False  # subset signal for cadre — Exec Cadre is NOT a separate participant_type
    student_type: Optional[str] = None
    squadron: Optional[str] = None
    flight: Optional[str] = None
    position: Optional[str] = None
    conflicts: Optional[str] = None
    highest_oride: Optional[str] = None
    paid: bool = False
    paid_in_full: bool = False
    amount_paid: Optional[float] = None
    registration_status: Optional[str] = None
    staff_member: bool = False
    unit_approved: bool = False
    unit_approval_date: Optional[str] = None
    wing_approved: bool = False
    wing_approval_date: Optional[str] = None
    slotted: bool = False
    address: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    cadet_parent_phone: Optional[str] = None
    cadet_parent_email: Optional[str] = None
    cadet_parent_phone_secondary: Optional[str] = None
    cadet_parent_phone_emergency: Optional[str] = None
    cadet_parent_email_secondary: Optional[str] = None
    cadet_parent_email_emergency: Optional[str] = None
    unit_cc_name: Optional[str] = None
    unit_cc_email: Optional[str] = None
    last_encampment: Optional[str] = None
    cppt_expiration: Optional[str] = None
    first_aid: Optional[str] = None
    # Application timestamp from eCAP roster column AI (`AppEditData`).
    # Drives the waitlist sort: earliest application gets the next free seat.
    app_edit_data: Optional[str] = None
    is100_date: Optional[str] = None
    is700_date: Optional[str] = None
    first_encampment: bool = True
    religious_preference: Optional[str] = None
    comments: Optional[str] = None
    notes: Optional[str] = None
    is_removed: Optional[bool] = False
    removed_at: Optional[str] = None
    removed_by: Optional[str] = None
    removal_reason: Optional[str] = None
    review_status: Optional[str] = None
    review_reason: Optional[str] = None
    review_flagged_at: Optional[str] = None
    review_flagged_by: Optional[str] = None

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantRemoval(BaseModel):
    removal_reason: str

class ParticipantResponse(ParticipantBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str
    updated_at: str
    manually_edited_at: Optional[str] = None
    manually_edited_by: Optional[str] = None
    # Read-only enrichments from the linked user account — populated by
    # /api/participants. Used by the Roster UI to render the correct
    # squadron/flight dropdowns for non-flight participants.
    linked_user_role: Optional[str] = None
    linked_support_section: Optional[str] = None
    is_non_flight: Optional[bool] = False
    is_support: Optional[bool] = False

class ScheduleEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    date: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    event_type: str = "general"
    target_groups: List[str] = ["all"]
    uniform: Optional[str] = None

class ScheduleEventCreate(ScheduleEventBase):
    pass

class ScheduleEventResponse(ScheduleEventBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_published: bool = False
    created_at: str
    updated_at: str

class ScheduleSettings(BaseModel):
    is_published: bool = False
    last_published_at: Optional[str] = None
    last_modified_at: Optional[str] = None
    version: int = 0

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]

class PushNotificationRequest(BaseModel):
    title: str
    body: str
    target_groups: List[str] = ["all"]
    url: Optional[str] = "/schedule"

class BudgetItemBase(BaseModel):
    category: str
    subcategory: Optional[str] = None
    item_name: str
    estimated: float = 0.0
    actual: float = 0.0
    notes: Optional[str] = None
    receipt_url: Optional[str] = None
    receipt_filename: Optional[str] = None
    payment_status: str = "pending"
    payment_date: Optional[str] = None
    vendor: Optional[str] = None
    item_type: str = "expense"

class BudgetItemCreate(BudgetItemBase):
    pass

class BudgetItemResponse(BudgetItemBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str
    updated_at: str

class FoodExpenseSettings(BaseModel):
    cost_per_person_per_day: float = 13.15
    total_participants: int = 0
    total_days: int = 8
    notes: Optional[str] = None

class FoodExpenseSettingsUpdate(BaseModel):
    cost_per_person_per_day: Optional[float] = None
    total_participants: Optional[int] = None
    total_days: Optional[int] = None
    notes: Optional[str] = None

class ScoreCategoryBase(BaseModel):
    name: str
    category_type: str
    max_points: float = 100.0
    description: Optional[str] = None
    is_active: bool = True

class ScoreCategoryCreate(ScoreCategoryBase):
    pass

class ScoreCategoryResponse(ScoreCategoryBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str

class ScoreEntryBase(BaseModel):
    category_id: str
    target_type: str
    target_id: str
    target_name: Optional[str] = None
    points: float
    date: str
    notes: Optional[str] = None

class ScoreEntryCreate(ScoreEntryBase):
    pass

class ScoreEntryResponse(ScoreEntryBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    category_name: Optional[str] = None
    entered_by: Optional[str] = None
    created_at: str

class MeritDemeritEntry(BaseModel):
    participant_id: str
    participant_name: Optional[str] = None
    entry_type: str
    points: float
    reason: str
    date: str

class MeritDemeritResponse(MeritDemeritEntry):
    model_config = ConfigDict(extra="ignore")
    id: str
    entered_by: Optional[str] = None
    created_at: str

class DailyAward(BaseModel):
    award_type: str
    date: str
    winner_id: str
    winner_name: str
    total_points: float
    notes: Optional[str] = None

class FlightReportSection(BaseModel):
    content: str = ""
    has_issues: bool = False

class FlightReportBase(BaseModel):
    report_date: str
    flight: str
    squadron: str
    reporter_role: str
    morale: FlightReportSection = FlightReportSection()
    safety_concerns: FlightReportSection = FlightReportSection()
    discipline_issues: FlightReportSection = FlightReportSection()
    training_performance: FlightReportSection = FlightReportSection()
    significant_events: FlightReportSection = FlightReportSection()
    recommendations: FlightReportSection = FlightReportSection()
    commander_issues: FlightReportSection = FlightReportSection()

class FlightReportCreate(FlightReportBase):
    pass

class FlightReportResponse(FlightReportBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    submitted_by: str
    submitted_by_name: str
    status: str
    escalation_level: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    escalation_history: Optional[List[dict]] = []
    created_at: str
    updated_at: str

class EscalateReportRequest(BaseModel):
    escalate_to: str
    notes: Optional[str] = None

class ReportDeadlineSettings(BaseModel):
    deadline_time: str = "21:00"
    reminder_minutes_before: int = 60
    is_enabled: bool = True

class DocumentBase(BaseModel):
    title: str
    description: Optional[str] = None
    doc_type: str
    category: Optional[str] = None
    content: Optional[str] = None
    file_url: Optional[str] = None
    storage_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    flight: Optional[str] = None
    squadron: Optional[str] = None
    scope: str = "global"

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str
    updated_at: str
    uploaded_by: Optional[str] = None
    version: int = 1
    version_history: Optional[List[Dict[str, Any]]] = None

class OrgChartRoleBase(BaseModel):
    role_id: str
    position_title: str
    assigned_name: Optional[str] = ""
    reports_to: Optional[str] = None
    secondary_reports_to: Optional[str] = None
    role_category: Optional[str] = ""
    order: int = 0
    display_label: Optional[str] = ""
    job_description: Optional[str] = ""
    responsible_for: Optional[str] = ""
    supervises: Optional[str] = ""

class OrgChartRoleCreate(OrgChartRoleBase):
    pass

class OrgChartRoleUpdate(BaseModel):
    position_title: Optional[str] = None
    assigned_name: Optional[str] = None
    reports_to: Optional[str] = None
    secondary_reports_to: Optional[str] = None
    role_category: Optional[str] = None
    order: Optional[int] = None
    display_label: Optional[str] = None
    job_description: Optional[str] = None
    responsible_for: Optional[str] = None
    supervises: Optional[str] = None

class OrgChartRoleResponse(OrgChartRoleBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    children: List[str] = []
    created_at: str
    updated_at: str

class GoogleSheetConfig(BaseModel):
    sheet_type: str
    spreadsheet_id: str
    gid: str
    name: Optional[str] = None
    enabled: bool = True

class UniformOfTheDay(BaseModel):
    uniform_code: str
    uniform_code_2: Optional[str] = None
    cadet_uniform_code: Optional[str] = None
    description: Optional[str] = None
    description_2: Optional[str] = None
    cadet_description: Optional[str] = None
    special_instructions: Optional[str] = None

class WeatherFlagUpdate(BaseModel):
    flag_color: str
    heat_index: Optional[float] = None
    wbgt: Optional[float] = None
    notes: Optional[str] = None

class DailySettingsUpdate(BaseModel):
    uniform: Optional[UniformOfTheDay] = None
    weather_flag: Optional[WeatherFlagUpdate] = None

class GoogleSheetsSettings(BaseModel):
    # Roster sheet sync was REMOVED in Phase 8 (Feb 2026). The roster is now
    # the source-of-truth on the backend; uploads go via the spreadsheet
    # upload flow (Sync Mode). The field is intentionally absent here.
    schedules: List["ScheduleSheetConfig"] = []
    org_chart_sheets: List[GoogleSheetConfig] = []
    sync_interval_hours: int = 1
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None
    last_sync_message: Optional[str] = None
    auto_sync_enabled: bool = True


class ScheduleSheetConfig(BaseModel):
    """A named Google Sheet that auto-syncs into the schedule.

    Multiple schedules can be configured (e.g. CAST weekend + main Encampment
    week) and synced independently — events imported from one configured
    schedule are tagged with `source_schedule_id` so re-syncing one doesn't
    touch the other.

    Tab resolution: when both `gid` and `sheet_name` are blank, the first
    tab is used. When `gid` is set, it takes priority. Otherwise `sheet_name`
    (resolved via the gviz CSV endpoint) is used. `sheet_name` is set by the
    "Discover tabs" auto-import flow.
    """
    id: str                              # stable key, e.g. "cast" or "encampment"
    label: str                           # human display name
    spreadsheet_id: str                  # Google Sheets doc id
    gid: Optional[str] = None            # optional tab gid (default: first tab)
    sheet_name: Optional[str] = None     # alternative to gid — exact tab name
    enabled: bool = True
    # Last-sync telemetry written by the scheduler:
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None   # "success" | "error" | "running"
    last_sync_message: Optional[str] = None
    last_event_count: Optional[int] = None


class GoogleSheetsSyncRequest(BaseModel):
    # Phase 8: only schedule + org-chart sheets are managed here.
    schedules: Optional[List[ScheduleSheetConfig]] = None
    org_chart_spreadsheet_id: Optional[str] = None
    org_chart_gids: Optional[List[str]] = None
    sync_interval_hours: int = 1
    auto_sync_enabled: bool = True

GoogleSheetsSettings.model_rebuild()

class BunkAssignRequest(BaseModel):
    participant_id: str
    bunk_number: int = 0
    position: str = "top"

class CheckInStepRequest(BaseModel):
    step: str
    notes: str = ""

class NotificationPreferences(BaseModel):
    schedule_changes: bool = True
    daily_digest: bool = True
    announcements: bool = True
    email_enabled: bool = True
    in_app_enabled: bool = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
