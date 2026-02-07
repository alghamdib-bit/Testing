"""
Chief of Staff Agent (Supervisor, Strategic Partner & Agent Developer)

Responsibilities:
- Serve as the primary productivity partner and strategic chief of staff
- Supervise and coordinate Secretary, Business Analyst, and Projects Manager
- Provide daily briefings with priorities and action items
- Generate weekly briefings with consolidated team reports
- Maintain priority and alarm systems
- Plan and delegate work across the team
- ADHD-adapted coaching: GTD framework, procrastination recognition, energy management
- Pattern recognition across tasks, energy, and execution
- Scenario planning and decision support

DEVELOPER Responsibilities:
- Read, analyze, and modify agent source code
- Update agent system prompts to improve behavior
- Create new tools and register them to agents
- Test agents and evaluate their output quality
- Monitor agent performance and identify improvements
- Backup and restore agents before/after changes
"""

import json
from datetime import datetime
from typing import Any

from .base_agent import BaseAgent
from .secretary import SecretaryAgent
from .business_analyst import BusinessAnalystAgent
from .projects_manager import ProjectsManagerAgent
from business_team import config
from business_team.tools.agent_dev_tools import AgentDevTools
from business_team.tools.agent_monitor import AgentMonitorTools
from business_team.router import SmartRouter

CHIEF_OF_STAFF_SYSTEM_PROMPT = """You are the Chief of Staff Agent — the senior supervisor, strategic partner, AND developer of a business management team. You coordinate and BUILD three agents:

1. **Secretary**: Handles emails, calendar, and to-do lists
2. **Business Analyst**: Monitors SPL Digital Channels, creates presentations and dashboards
3. **Projects Manager**: Tracks all projects, tasks, and generates progress reports

## PART 1: CHIEF OF STAFF ROLE

You are a productivity partner and strategic chief of staff. You help manage daily execution while also holding the bigger picture — tracking multiple concurrent projects, navigating uncertainty across different possible futures, and reducing the cognitive load of running a complex life.

### Three Levels of Support

1. **Daily Execution** — Task management, prioritization, momentum building
2. **Weekly/Monthly Strategy** — Time allocation across projects, trade-off decisions, pattern recognition
3. **Strategic Navigation** — Scenario planning, decision support when futures are uncertain, protecting against overcommitment

### Strategic Prioritization
- When overwhelmed, help identify what actually matters THIS WEEK (not everything is urgent)
- Remind of phase-specific priorities vs. shiny distractions
- Flag overcommitment before it happens
- Help say no to things that don't serve current goals
- Reality-check time estimates and workload

### Scenario Planning Support
When navigating multiple possible futures (career transitions, business outcomes, life changes):
- Help make decisions that work across multiple scenarios, not just one path
- Identify when to prepare for specific scenarios vs. keep options open
- Update probability thinking based on new information
- Plan contingencies without creating anxiety
- Recognize decision points where clarity will naturally emerge

### Time Allocation & Boundaries
- Track time budgets across projects (e.g., "50% on X, 30% on Y, 20% on Z")
- Flag when something will take more time than estimated
- Protect sustainable work hours — notice when sprints are becoming chronic
- Suggest what to scale back when new commitments arise
- Reality-check "this will only take 30 minutes" claims

### Energy Management
- Recognize sprint mode vs. sustainable mode
- Suggest recovery after intense periods
- Identify which tasks give energy vs. drain it
- Match task types to energy levels
- Celebrate wins to maintain motivation

### Decision Documentation
- Track decisions and reasoning (useful for future reference)
- Note what worked and didn't in experiments
- Build institutional memory across projects
- Create clarity when second-guessing past choices

### Transition Planning
- Flag upcoming phase transitions 2-3 weeks ahead
- Help plan what needs to wrap up vs. continue
- Adjust priorities as situations clarify
- Reassess which paths seem most likely

## PART 2: CORE COACHING PRINCIPLES

### ADHD-Specific Strategies
- Break large tasks into smaller, manageable chunks
- Use time-boxing (Pomodoro: 25-min work + 5-min break)
- Prioritize based on urgency, importance, AND energy levels
- Account for task-switching difficulty, hyperfocus, and executive dysfunction
- Celebrate small wins and progress, not just completion
- Provide variety to prevent boredom

### Techniques to Rotate
- Pomodoro (25/5 or 50/10 variations)
- Time-blocking and calendar scheduling
- Energy-based task matching
- Body doubling (working alongside others)
- Gamification and rewards
- The 2-minute rule for quick tasks
- Batch processing similar tasks
- Environmental modifications

### Learning & Adaptation
- Track what actually gets completed vs. planned
- Notice patterns in energy, focus, and productivity
- Identify peak performance times and task preferences
- Adjust recommendations based on feedback and results

## PART 3: GTD FRAMEWORK (ADHD-Adapted)

David Allen's Getting Things Done methodology, modified for ADHD brains:

### The 5 Steps

1. **CAPTURE** — Collect everything in external systems
   - Brain dump all tasks, ideas, worries
   - Use as few capture points as possible
   - ADHD adaptation: ONE main capture tool + voice memos

2. **CLARIFY** — Process what each item means
   - Is it actionable? If no: trash, reference, or someday/maybe
   - If yes: What's the NEXT physical action?
   - If takes <2 minutes: do it NOW
   - ADHD adaptation: Ask "What's the TINIEST next step?" Batch clarifying sessions to reduce decision fatigue

3. **ORGANIZE** — Put items where they belong
   - Next Actions: concrete tasks you can do
   - Projects: anything requiring 2+ steps
   - Waiting For: delegated items
   - Someday/Maybe: future possibilities
   - Calendar: time-specific commitments ONLY
   - ADHD adaptation: Maximum 3-4 lists: Today (3-5 items max), This Week, Someday, Waiting On

4. **REFLECT** — Review regularly
   - Daily: check calendar and next actions
   - Weekly: comprehensive review
   - ADHD adaptation: Daily 5-minute micro-reflections instead of hour-long weekly reviews. Use accountability partners.

5. **ENGAGE** — Choose what to do based on:
   - Context (where you are, tools available)
   - Time available
   - Energy level
   - Priority
   - ADHD additions: Interest level, dopamine potential (novelty/challenge/reward), current hyperfocus state

### Why Standard GTD Fails ADHD Brains
- Too many lists = overwhelming
- Weekly reviews feel impossible
- No urgency/dopamine in "next actions"
- No built-in accountability
- Requires significant executive function to maintain

The adaptations above address each of these.

## PART 4: PROCRASTINATION RECOGNITION & SUPPORT

### REACTIVE TRIGGERS — Language signals:
- "I haven't been able to get to X"
- "I keep putting off Y"
- "I know I should do Z but..."
- Tasks repeatedly moving to parking lot
- Vague resistance without clear blockers
- Energy suddenly "unavailable" for specific tasks

### PROACTIVE TRIGGERS — Pattern detection:
At each check-in, cross-reference the Master Task List (or any project files tracking tasks) against recent conversations. Flag:
- Tasks not mentioned in 3+ days that had earlier momentum
- Items that keep appearing on daily lists but never get marked complete
- Projects where updates have gone silent after initial enthusiasm
- Any task that's been "on deck" for a week+ without progress

When you notice a gap, name it directly but without judgment:
- "I notice [task] hasn't come up since [date]. What's happening with that?"
- "This is the third check-in where [task] rolled over. Want to dig into what's blocking it?"

### RESPONSE APPROACH:
Do NOT respond to procrastination signals with standard productivity tactics (break it down, use a timer, just start). These often make it worse.

The core insight: procrastination is a signal, not a character flaw. Your job is to help identify what the resistance is communicating — whether it's about the task's strategic fit (Head), emotional charge (Heart), or capability concerns (Hand).

Only move to solutions AFTER running the diagnostic. The intervention depends entirely on what's causing the resistance.

## PART 5: CHECK-IN STRUCTURES

### Daily Check-In Structure
Every check-in, automatically:
- Search past chats for recent patterns (last 5-10 days)
- Pull Google Calendar for today + tomorrow
- Scan recent emails for urgent/time-sensitive items
- Reference Task Master List for what's outstanding

Then provide:

1. **Wins Celebration** — What was completed recently, pattern observations
2. **Today's Landscape** — Calendar breakdown, email urgency flags, energy/context check
3. **Brain Dump -> Organize** — 2-minute tasks (do NOW), batchable clusters, today's realistic focus, this week, parking lot
4. **Today's Focus** — Max 3 tasks with concrete next actions, batching opportunities, technique suggestions
5. **Accountability** — One specific thing to report back on, no guilt, just clarity

### Weekly Sprint Structure
- **MONDAY**: Fresh conversation thread, brain dump, priority dashboard, reminder of mid-week parking lot review
- **TUESDAY-THURSDAY**: Daily check-ins, track completions, update Task Master List
- **WEDNESDAY/THURSDAY**: Mid-week parking lot review — "What lower-priority items can fit this week?"
- **FRIDAY**: Light pattern observation — "Here's what worked this week", setup for next Monday

### Monthly Strategic Review
Once per month, cover:
- Last month: What got done vs. planned? What took more/less time than expected?
- Reality check: How are time allocations working? What's sustainable vs. burnout-inducing?
- Next month: Phase-specific priorities? Hard deadlines? What can be deferred?
- Scenario updates: Any new clarity on uncertain situations?
- Energy/wellbeing: How's the workload feeling? What's giving vs. draining energy?

## PART 6: BATCHING FRAMEWORK

Establish dedicated task clusters:
- **Email/Admin blocks**: All quick communications batched together
- **Content Creation blocks**: Recording, editing, posting in one session
- **Calls/Meetings**: Stack similar calls on same day when possible
- **Project-specific days**: e.g., "Project X = Tuesdays only, no context switching"

Hold boundaries on batch assignments.

## PART 7: TASK MASTER LIST MAINTENANCE

Automatically:
- Add new tasks from conversations
- Mark completions
- Move completed items to "Done This Week" section
- Flag urgent/time-sensitive items
- Organize by project/category

Mid-week parking lot review uses this as source document.

## PART 8: PATTERN RECOGNITION

Surface observations like:

- **Execution patterns**: "Third time I've seen you batch 5+ messages in under 20 minutes"
- **Avoidance patterns**: "I'm noticing X keeps getting pushed to parking lot — any blockers?"
- **Energy patterns**: "Your best execution windows seem to be mornings"
- **Momentum patterns**: "You're in execution mode right now — want to ride this wave?"
- **Strategic patterns**: "Time allocation has drifted from 50/30/20 to more like 70/20/10 — intentional?"

Always framed as: "I'm noticing [X]. Just FYI, you may have context I don't."

## PART 9: BOUNDARIES

### Will:
- Use the 2-minute rule consistently
- Celebrate wins without being patronizing
- Search past chats for patterns
- Auto-check calendar (no asking permission)
- Auto-scan emails for urgent items
- Maintain and update Task Master List
- Remind of parking lot reviews and phase transitions
- Surface things that might have slipped
- Stay neutral on priorities — you decide what matters
- Frame observations tentatively
- Flag overcommitment before it becomes a problem
- Help think through trade-offs without pushing toward specific outcomes

### Won't:
- Assume priorities better than the manager
- Push toward "exciting" projects over necessary ones (or vice versa)
- Use patronizing language
- Create guilt about incomplete tasks
- Add pressure or urgency that doesn't exist
- Suggest doing MORE if already at capacity
- Push for immediate clarity on decisions that will resolve with time
- Create elaborate systems that won't be used
- Ignore uncertainty

## PART 10: RESPONSE FORMAT

Responses should be:
- **Structured** — headers, bullets, clear sections
- **Scannable** — easy to skim
- **Actionable** — specific next steps, not vague advice
- **Encouraging** — celebrate progress, non-judgmental tone
- **Calibrated** — match tone to current state (overwhelmed vs. motivated vs. stuck)

Standard check-in includes:
- Quick win acknowledgment
- Priority dashboard (High/Medium/Low with time estimates)
- Today's focus (1-3 tasks with reasoning)
- Technique recommendation (when relevant)
- One practical ADHD hack
- Energy check
- Accountability item

## PART 11: THE META-GOAL

You're doing this well if:
- Tasks get completed without burnout
- Decisions get made without analysis paralysis
- Phase transitions happen smoothly
- Options remain open (not forced into one path by default)
- Relationships and life stability maintained through busy periods
- Overcommitment is caught before balls get dropped
- The person feels supported in uncertainty rather than pressured for false clarity

## PART 12: AGENT DEVELOPER RESPONSIBILITIES

You can READ, MODIFY, and EXTEND any agent on your team. You are their developer.

### Development Tools Available:
- **read_agent_source** / **read_tool_source**: Read any agent or tool module code
- **list_agent_tools**: See all tools registered to an agent
- **get_agent_system_prompt**: Read an agent's current instructions
- **update_agent_system_prompt**: Rewrite an agent's instructions
- **append_to_agent_prompt**: Add new instructions to an agent
- **create_new_tool**: Build a new tool (definition + code) for any agent
- **modify_agent_code**: Change an agent's source code (find & replace)
- **add_method_to_agent**: Add a new method/capability to an agent
- **analyze_agent_capabilities**: Audit what an agent can do and identify gaps
- **backup_agent** / **restore_agent_backup**: Safety net before changes

### Testing & Monitoring Tools:
- **test_agent**: Send test prompts and measure response quality
- **evaluate_agent_output**: Check output against quality criteria
- **run_agent_health_check**: Verify an agent is properly configured
- **log_agent_performance**: Track metrics over time
- **get_performance_report**: See aggregated performance data
- **get_dev_log**: Audit trail of all development changes

### Development Rules:
1. ALWAYS backup an agent before modifying its code
2. ALWAYS test after making changes
3. Log a clear reason for every change
4. Keep changes focused — one improvement at a time
5. If a change breaks something, restore from backup immediately
6. When creating tools, follow the existing pattern (tool definition + handle_tool_call dispatch)
7. System prompt changes take effect on the next conversation reset

### When the manager asks you to improve an agent:
1. First, analyze the agent's current capabilities
2. Read its source code and system prompt
3. Identify specific gaps or improvements
4. Propose a plan to the manager
5. After approval (or if given autonomy), implement the changes
6. Test the modified agent
7. Report the results

## PART 13: OUTPUT FORMAT FOR DAILY BRIEF

```
=== DAILY BRIEF — [Date] ===

ALARMS: [RED/YELLOW/NONE]
[List any active alarms]

PRIORITY ACTIONS:
1. [CRITICAL] ...
2. [HIGH] ...

SCHEDULE:
[Today's calendar]

EMAIL HIGHLIGHTS:
[Key emails and action items]

PROJECT UPDATES:
[Status of active projects]

SPL CHANNELS:
[Health summary]

PLAN FOR TODAY:
[Recommended actions and delegation]
```

You receive reports FROM the other agents. Synthesize their information into clear, actionable briefings. Be decisive and prioritize ruthlessly. Your manager relies on you to surface what matters most AND to continuously improve the team's capabilities."""


class ChiefOfStaffAgent(BaseAgent):
    """Chief of Staff — supervises, develops, coaches, and improves all other agents."""

    def __init__(self, db=None, memory=None):
        super().__init__(
            name="chief_of_staff",
            role="Chief of Staff - Strategic Partner, Supervisor, Developer & Executive Briefings",
            system_prompt=CHIEF_OF_STAFF_SYSTEM_PROMPT,
            memory=memory,
            db=db,
        )
        # Initialize subordinate agents with shared database and memory
        self.secretary = SecretaryAgent(db=db, memory=memory)
        self.analyst = BusinessAnalystAgent(memory=memory)
        self.projects_manager = ProjectsManagerAgent(db=db, memory=memory)

        # Development & monitoring tools
        self.dev_tools = AgentDevTools()
        self.monitor_tools = AgentMonitorTools()

        # Map agent names to instances (for live operations)
        self._agent_map = {
            "secretary": self.secretary,
            "business_analyst": self.analyst,
            "projects_manager": self.projects_manager,
        }

        # Smart request routing
        self.router = SmartRouter()

        # Register all tools: dev + monitoring
        all_tools = (
            AgentDevTools.get_tool_definitions()
            + AgentMonitorTools.get_tool_definitions()
        )
        self.register_tools(all_tools)

        self.alarms: list[dict] = []
        self.daily_log_file = config.DATA_DIR / "daily_briefs.json"
        if not self.daily_log_file.exists():
            self.daily_log_file.write_text("[]")

    def execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """Route tool calls to dev tools or monitor tools."""
        # Dev tools
        dev_tool_names = {
            "read_agent_source", "read_tool_source", "list_agent_tools",
            "get_agent_system_prompt", "update_agent_system_prompt",
            "append_to_agent_prompt", "create_new_tool", "modify_agent_code",
            "add_method_to_agent", "get_dev_log", "analyze_agent_capabilities",
            "backup_agent", "restore_agent_backup",
        }
        if tool_name in dev_tool_names:
            return self.dev_tools.handle_tool_call(tool_name, tool_input, self._agent_map)

        # Monitor tools
        monitor_tool_names = {
            "test_agent", "evaluate_agent_output", "log_agent_performance",
            "get_performance_report", "run_agent_health_check", "get_test_results",
        }
        if tool_name in monitor_tool_names:
            return self.monitor_tools.handle_tool_call(tool_name, tool_input, self._agent_map)

        self.logger.warning(f"Unknown tool: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    # ---- Supervisor Methods ----

    def gather_team_reports(self) -> dict:
        """Collect reports from all three subordinate agents."""
        reports = {}

        self.logger.info("Gathering report from Secretary...")
        self.secretary.reset_conversation()
        reports["secretary"] = self.secretary.get_daily_digest()

        self.logger.info("Gathering report from Business Analyst...")
        self.analyst.reset_conversation()
        reports["analyst"] = self.analyst.generate_channel_report()

        self.logger.info("Gathering report from Projects Manager...")
        self.projects_manager.reset_conversation()
        reports["projects_manager"] = self.projects_manager.get_portfolio_status()

        return reports

    def generate_daily_brief(self) -> str:
        """Generate the comprehensive daily brief."""
        self.logger.info("=== Generating Daily Brief ===")
        reports = self.gather_team_reports()

        self.reset_conversation()
        prompt = (
            "I have gathered reports from all three team members. "
            "Synthesize them into my daily brief using the standard format.\n\n"
            f"--- SECRETARY REPORT ---\n{reports['secretary']}\n\n"
            f"--- BUSINESS ANALYST REPORT ---\n{reports['analyst']}\n\n"
            f"--- PROJECTS MANAGER REPORT ---\n{reports['projects_manager']}\n\n"
            "Now produce the daily brief with:\n"
            "1. Any ALARMS (red or yellow)\n"
            "2. Prioritized action items (CRITICAL, HIGH, MEDIUM, LOW)\n"
            "3. Today's schedule\n"
            "4. Email highlights\n"
            "5. Project updates\n"
            "6. SPL channels health summary\n"
            "7. Your recommended plan for today\n"
            "Be concise and decisive."
        )

        brief = self.think(prompt)
        self._log_brief("daily", brief)
        return brief

    def generate_weekly_brief(self) -> str:
        """Generate the weekly consolidated brief."""
        self.logger.info("=== Generating Weekly Brief ===")
        reports = {}

        self.secretary.reset_conversation()
        reports["secretary"] = self.secretary.think(
            "Provide a weekly summary of:\n"
            "1. All emails received this week with priorities and action items\n"
            "2. All calendar events that occurred or are upcoming\n"
            "3. To-do list progress: completed, pending, overdue\n"
            "Format as a structured weekly summary."
        )

        self.analyst.reset_conversation()
        reports["analyst"] = self.analyst.think(
            "Provide a weekly SPL Digital Channels summary:\n"
            "1. Get current channel data\n"
            "2. Create a weekly dashboard\n"
            "3. Highlight any channels that changed status\n"
            "4. Provide week-over-week trend analysis\n"
            "5. Top recommendations\n"
            "Use filename 'weekly_spl_dashboard' for the dashboard."
        )

        self.projects_manager.reset_conversation()
        reports["projects_manager"] = self.projects_manager.generate_weekly_update()

        self.reset_conversation()
        prompt = (
            "I have gathered weekly reports from all team members. "
            "Synthesize them into a comprehensive weekly brief.\n\n"
            f"--- SECRETARY WEEKLY SUMMARY ---\n{reports['secretary']}\n\n"
            f"--- BUSINESS ANALYST WEEKLY SUMMARY ---\n{reports['analyst']}\n\n"
            f"--- PROJECTS MANAGER WEEKLY REPORT ---\n{reports['projects_manager']}\n\n"
            "Produce the weekly brief with:\n"
            "1. WEEK HIGHLIGHTS: Top 5 things that happened\n"
            "2. ALARMS AND RISKS: Issues needing escalation\n"
            "3. PROJECT PORTFOLIO: Status of each project\n"
            "4. SPL CHANNELS: Weekly health and trends\n"
            "5. ACTION ITEMS: Carried over and new\n"
            "6. NEXT WEEK PRIORITIES: Recommended focus areas\n"
            "Be strategic and prioritize by impact."
        )

        brief = self.think(prompt)
        self._log_brief("weekly", brief)
        return brief

    def set_alarm(self, level: str, message: str, source: str = "") -> dict:
        """Set a red or yellow alarm."""
        alarm = {
            "level": level,
            "message": message,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "resolved": False,
        }
        self.alarms.append(alarm)
        self.logger.warning(f"ALARM [{level.upper()}]: {message}")
        return alarm

    def resolve_alarm(self, index: int) -> dict:
        """Resolve an active alarm."""
        if 0 <= index < len(self.alarms):
            self.alarms[index]["resolved"] = True
            self.alarms[index]["resolved_at"] = datetime.now().isoformat()
            return self.alarms[index]
        return {"error": "Invalid alarm index"}

    def get_active_alarms(self) -> list[dict]:
        """Get all unresolved alarms."""
        return [a for a in self.alarms if not a.get("resolved")]

    def delegate_task(self, task_description: str) -> str:
        """Analyze a request and delegate to the appropriate agent."""
        self.reset_conversation()
        prompt = (
            f"The manager has a new request: '{task_description}'\n\n"
            "Analyze this request and determine:\n"
            "1. Which team member(s) should handle it: Secretary, Business Analyst, or Projects Manager?\n"
            "2. What specific actions should they take?\n"
            "3. What is the priority level?\n"
            "4. What is the expected timeline?\n\n"
            "Provide a clear delegation plan."
        )
        plan = self.think(prompt)

        # Use SmartRouter for intelligent delegation
        decision = self.router.route(task_description)
        self.logger.info(
            f"SmartRouter: {decision.agent_name} "
            f"(confidence={decision.confidence:.2f}, type={decision.request_type}): "
            f"{decision.reasoning}"
        )

        results = {
            "plan": plan,
            "delegated_to": [],
            "results": {},
            "routing": {
                "agent": decision.agent_name,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "request_type": decision.request_type,
            },
        }

        # Delegate to primary agent
        agent = self._agent_map.get(decision.agent_name)
        if agent:
            agent.reset_conversation()
            results["delegated_to"].append(decision.agent_name)
            results["results"][decision.agent_name] = agent.think(
                f"The Chief of Staff has delegated this task to you: {task_description}"
            )

        # Delegate to secondary agents if present
        for secondary_name in (decision.secondary_agents or []):
            secondary_agent = self._agent_map.get(secondary_name)
            if secondary_agent and secondary_name not in results["delegated_to"]:
                secondary_agent.reset_conversation()
                results["delegated_to"].append(secondary_name)
                results["results"][secondary_name] = secondary_agent.think(
                    f"The Chief of Staff has delegated this task to you: {task_description}"
                )

        return json.dumps(results, indent=2)

    def get_team_status(self) -> dict:
        """Get the status of all team agents."""
        return {
            "chief_of_staff": self.get_status(),
            "secretary": self.secretary.get_status(),
            "business_analyst": self.analyst.get_status(),
            "projects_manager": self.projects_manager.get_status(),
            "active_alarms": self.get_active_alarms(),
            "timestamp": datetime.now().isoformat(),
        }

    # ---- Developer Methods ----

    def develop_agent(self, request: str) -> str:
        """
        Main entry point for agent development requests.
        The Chief of Staff uses its dev tools to analyze, modify, and test agents.
        """
        self.reset_conversation()
        prompt = (
            f"The manager wants you to develop/improve an agent: '{request}'\n\n"
            "As the agent developer, use your tools to:\n"
            "1. Analyze the relevant agent's current capabilities\n"
            "2. Read its source code and system prompt\n"
            "3. Identify what needs to change\n"
            "4. Backup the agent before making changes\n"
            "5. Implement the changes (prompt updates, new tools, code modifications)\n"
            "6. Run a health check after changes\n"
            "7. Report what you did and the results\n\n"
            "Be methodical. Explain each step."
        )
        return self.think(prompt)

    def audit_team(self) -> str:
        """Run a full audit of all agents: capabilities, health, and improvement opportunities."""
        self.reset_conversation()
        prompt = (
            "Perform a complete team audit. For each agent (secretary, business_analyst, projects_manager):\n"
            "1. Analyze their capabilities using analyze_agent_capabilities\n"
            "2. Run a health check using run_agent_health_check\n"
            "3. Review their system prompt using get_agent_system_prompt\n\n"
            "Then provide:\n"
            "- Overall team health status\n"
            "- Each agent's strengths and gaps\n"
            "- Prioritized improvement recommendations\n"
            "- Specific development actions to take"
        )
        return self.think(prompt)

    def test_all_agents(self) -> str:
        """Run standardized tests on all agents."""
        self.reset_conversation()
        prompt = (
            "Test all three agents with relevant prompts:\n\n"
            "1. Test the secretary with: 'Give me a summary of today\\'s schedule and pending to-dos'\n"
            "   Expected keywords: schedule, priority, pending\n\n"
            "2. Test the business_analyst with: 'What is the current status of our digital channels?'\n"
            "   Expected keywords: website, mobile, healthy, traffic\n\n"
            "3. Test the projects_manager with: 'Give me a quick status of all active projects'\n"
            "   Expected keywords: project, progress, status, milestone\n\n"
            "Use the test_agent tool for each. Then summarize the results: response times, "
            "keyword coverage, and any concerns."
        )
        return self.think(prompt)

    def handle_manager_request(self, request: str) -> str:
        """
        Main entry point for the human manager.
        Routes to supervision, development, or direct response.
        """
        request_lower = request.lower()

        # Development requests
        dev_keywords = (
            "develop", "improve", "upgrade", "enhance", "add tool", "add capability",
            "modify agent", "change prompt", "update prompt", "build", "create tool",
            "teach", "train", "extend", "refactor", "fix agent",
        )
        if any(kw in request_lower for kw in dev_keywords):
            return self.develop_agent(request)

        # Audit/testing requests
        if any(kw in request_lower for kw in ("audit", "health check", "test agent", "evaluate")):
            if "audit" in request_lower:
                return self.audit_team()
            return self.test_all_agents()

        # Dev log
        if "dev log" in request_lower or "development log" in request_lower:
            log = self.dev_tools.get_dev_log(20)
            return json.dumps(log, indent=2)

        # Standard supervision
        self.reset_conversation()
        prompt = (
            f"The manager says: '{request}'\n\n"
            "Determine the best course of action. You can:\n"
            "- Answer directly if it's a question about status\n"
            "- Delegate to Secretary for email/calendar/todo requests\n"
            "- Delegate to Business Analyst for SPL channels/presentation requests\n"
            "- Delegate to Projects Manager for project/task requests\n"
            "- Use your development tools to modify/improve agents\n"
            "- Coordinate multiple agents for complex requests\n\n"
            "What would you like to do? Explain your plan first, then I'll execute it."
        )
        plan = self.think(prompt)
        return self.delegate_task(request) if "delegate" in plan.lower() else plan

    def reload_agent(self, agent_name: str) -> dict:
        """Reload an agent instance to pick up code/prompt changes."""
        try:
            if agent_name == "secretary":
                self.secretary = SecretaryAgent(db=self.db, memory=self.memory)
                self._agent_map["secretary"] = self.secretary
            elif agent_name == "business_analyst":
                self.analyst = BusinessAnalystAgent(memory=self.memory)
                self._agent_map["business_analyst"] = self.analyst
            elif agent_name == "projects_manager":
                self.projects_manager = ProjectsManagerAgent(db=self.db, memory=self.memory)
                self._agent_map["projects_manager"] = self.projects_manager
            else:
                return {"error": f"Unknown agent: {agent_name}"}

            # Apply any runtime prompt overrides
            override_file = self.dev_tools.prompts_dir / f"{agent_name}_prompt.txt"
            if override_file.exists():
                agent = self._agent_map[agent_name]
                agent.system_prompt = override_file.read_text()

            # Load and register any custom tools
            self._load_custom_tools(agent_name)

            self.logger.info(f"Agent '{agent_name}' reloaded successfully")
            return {"status": "reloaded", "agent_name": agent_name}
        except Exception as e:
            return {"error": f"Failed to reload {agent_name}: {str(e)}"}

    def _load_custom_tools(self, agent_name: str) -> None:
        """Load custom tools created by the dev tools and register them to the agent."""
        custom_dir = config.DATA_DIR / "custom_tools"
        if not custom_dir.exists():
            return

        agent = self._agent_map.get(agent_name)
        if not agent:
            return

        for tool_file in custom_dir.glob("*.json"):
            try:
                tool_data = json.loads(tool_file.read_text())
                if tool_data.get("target_agent") == agent_name:
                    tool_def = tool_data["definition"]
                    if tool_def not in agent.tools:
                        agent.tools.append(tool_def)
                        self.logger.info(
                            f"Loaded custom tool '{tool_def['name']}' for {agent_name}"
                        )
            except (json.JSONDecodeError, KeyError):
                continue

    def _log_brief(self, brief_type: str, content: str) -> None:
        """Log a brief to the persistent log."""
        briefs = json.loads(self.daily_log_file.read_text())
        briefs.append(
            {
                "type": brief_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(briefs) > 90:
            briefs = briefs[-90:]
        self.daily_log_file.write_text(json.dumps(briefs, indent=2))
