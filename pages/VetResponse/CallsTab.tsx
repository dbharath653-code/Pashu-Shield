import { useCallback, useEffect, useState } from "react";
import { Phone, PhoneOff, PhoneIncoming, RefreshCw, Voicemail, FlaskConical, ChevronRight, X } from "lucide-react";
import { apiErrorMessage } from "../../services/apiAuth";

/**
 * IVR & Calls section of the existing Veterinary Response dashboard.
 *   - Active Calls / Call History  -> GET /api/v1/telephony/calls
 *   - Callback Queue               -> GET /api/v1/callbacks (+ accept / call back / create case / complete)
 *   - "Simulate Incoming Farmer Call" (DEMO_MODE, MockTelephonyProvider, labelled DEMO / SIMULATED)
 * Phone numbers arrive already masked by the backend unless the viewer has PII permission.
 */

/** Main-menu digit -> the label shown on the dashboard (mirrors backend services/ivr/menu.py). */
const MENU_LABEL: Record<string, string> = {
  "1": "Report sick animal",
  "2": "Request veterinarian",
  "3": "Case status",
  "0": "Emergency",
};

type CallRow = {
  id: string;
  provider: string;
  callSid: string;
  callerPhone: string | null;
  callerMasked: boolean;
  language: string | null;
  district: string | null;
  status: string;
  farmerId: string | null;
  reportId: string | null;
  recordingStatus: string;
  transcriptionStatus: string;
  aiSummary: string | null;
  ivrMenuOption: string | null;
  isEmergency: boolean;
  isSimulated: boolean;
  demoLabel: string | null;
  isActive: boolean;
  startedAt: string | null;
  endedAt: string | null;
  lastError: string | null;
};

type CallDetail = CallRow & {
  farmerName: string | null;
  veterinarianName: string | null;
  village: string | null;
  species: string | null;
  numberAffected: number | null;
  symptoms: string[] | null;
  triageRiskLevel: string | null;
  reportNumber: string | null;
  callback: { id: string; status: string; priority: string } | null;
  survey: { id: string; status: string; language: string | null; currentQuestion: string | null } | null;
  answers: { question: string; answer: string | null; normalized: unknown; at: string | null }[];
  vetAttempts: { vet_id?: string; phone_tail?: string; result?: string }[];
  transcript?: { segments: { id: string; speaker: string; text: string }[] } | null;
};

type CallbackRow = {
  id: string;
  callSessionId: string | null;
  reportId: string | null;
  callerPhone: string | null;
  district: string | null;
  taluka: string | null;
  village: string | null;
  species: string | null;
  symptoms: string[];
  priority: "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | string;
  status: string;
  assignedVeterinarian: string | null;
  notes: string | null;
  isSimulated: boolean;
  demoLabel: string | null;
  callTime: string | null;
};

async function failMessage(res: Response, fallback: string): Promise<Error> {
  try {
    return new Error(apiErrorMessage(await res.json(), fallback));
  } catch {
    return new Error(`${fallback} (${res.status})`);
  }
}

const PRIORITY_CLASS: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH: "bg-orange-100 text-orange-800",
  MODERATE: "bg-yellow-100 text-yellow-800",
  LOW: "bg-green-100 text-green-800",
};

const STATUS_CLASS = (s: string) =>
  ["COMPLETED", "ACCEPTED", "IN_PROGRESS"].includes(s)
    ? "bg-green-100 text-green-800"
    : ["FAILED", "CANCELLED"].includes(s)
      ? "bg-red-100 text-red-800"
      : s === "PENDING"
        ? "bg-yellow-100 text-yellow-800"
        : "bg-blue-100 text-blue-800";

function riskPill(risk: string | null) {
  if (!risk) return null;
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${PRIORITY_CLASS[risk] || "bg-gray-100 text-gray-700"}`}>
      TRIAGE {risk}
    </span>
  );
}

export default function CallsTab() {
  const [sub, setSub] = useState<"active" | "history" | "callbacks">("active");
  const [calls, setCalls] = useState<CallRow[]>([]);
  const [callbacks, setCallbacks] = useState<CallbackRow[]>([]);
  const [detail, setDetail] = useState<CallDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simBusy, setSimBusy] = useState(false);
  const [simResult, setSimResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const active = sub === "active" ? "?active=true" : sub === "history" ? "?active=false" : "";
      if (sub === "callbacks") {
        const res = await fetch("/api/v1/callbacks?limit=200");
        if (!res.ok) throw await failMessage(res, `Callback queue failed (${res.status})`);
        setCallbacks(await res.json());
      } else {
        const res = await fetch(`/api/v1/telephony/calls${active}`);
        if (!res.ok) throw await failMessage(res, `Calls failed (${res.status})`);
        setCalls(await res.json());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [sub]);

  useEffect(() => {
    load();
    const t = window.setInterval(load, 12000); // live refresh alongside the existing WebSocket banner
    return () => window.clearInterval(t);
  }, [load]);

  const openDetail = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/telephony/calls/${id}`);
      if (!res.ok) throw await failMessage(res, "Failed to load call");
      const d: CallDetail = await res.json();
      try {
        const tr = await fetch(`/api/v1/telephony/calls/${id}/transcript`);
        if (tr.ok) d.transcript = await tr.json();
      } catch {
        /* transcript optional */
      }
      setDetail(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load call");
    }
  };

  const callbackAction = async (id: string, action: "accept" | "call-back" | "complete" | "create-case") => {
    try {
      const res = await fetch(`/api/v1/callbacks/${id}/${action}`, { method: "POST" });
      if (!res.ok) throw await failMessage(res, "Action failed");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    }
  };

  const closeCall = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/telephony/calls/${id}/close`, { method: "POST" });
      if (!res.ok) throw await failMessage(res, "Close failed");
      setDetail(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Close failed");
    }
  };

  const simulate = async (scenario: "vet_available" | "vet_unavailable") => {
    setSimBusy(true);
    setSimResult(null);
    try {
      const res = await fetch("/api/v1/telephony/demo/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: "en", scenario }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(apiErrorMessage(body, `Simulation failed (${res.status})`));
      setSimResult(
        `${body.label}: ${scenario} — steps: ${body.steps.join(" → ")}` +
          (body.reportId ? ` | report ${body.reportId}` : "") +
          (body.callbackId ? ` | callback ${body.callbackId}` : ""),
      );
      await load();
    } catch (e) {
      setSimResult(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setSimBusy(false);
    }
  };

  const time = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      <div className="p-4 border-b border-gray-200 bg-gray-50 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {(
            [
              ["active", "Active Calls", <PhoneIncoming key="a" size={16} />],
              ["history", "Call History", <Phone key="b" size={16} />],
              ["callbacks", "Callback Queue", <Voicemail key="c" size={16} />],
            ] as const
          ).map(([key, label, icon]) => (
            <button
              key={key}
              onClick={() => setSub(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border ${
                sub === key ? "bg-brandBlue text-white border-brandBlue" : "bg-white border-gray-300 text-gray-600 hover:bg-gray-100"
              }`}
            >
              {icon}
              {label}
              {key === "callbacks" && callbacks.filter((c) => c.status === "PENDING").length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full bg-red-500 text-white text-xs">
                  {callbacks.filter((c) => c.status === "PENDING").length}
                </span>
              )}
            </button>
          ))}
          <button onClick={load} className="p-2 rounded-lg border border-gray-300 text-gray-500 hover:bg-gray-100" title="Refresh">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => simulate("vet_unavailable")}
            disabled={simBusy}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-purple-400 text-purple-700 text-sm hover:bg-purple-50 disabled:opacity-50"
            title="Uses MockTelephonyProvider — never a real Exotel call"
          >
            <FlaskConical size={16} /> Simulate Incoming Farmer Call
          </button>
          <button
            onClick={() => simulate("vet_available")}
            disabled={simBusy}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-purple-400 text-purple-700 text-sm hover:bg-purple-50 disabled:opacity-50"
          >
            <FlaskConical size={16} /> Simulate (vet available)
          </button>
        </div>
      </div>

      {simResult && (
        <div className="px-4 py-2 bg-purple-50 border-b border-purple-100 text-sm text-purple-800 flex justify-between items-center">
          <span>{simResult}</span>
          <button onClick={() => setSimResult(null)}><X size={14} /></button>
        </div>
      )}
      {error && <div className="px-4 py-2 bg-red-50 border-b border-red-100 text-sm text-red-700">{error}</div>}

      {detail ? (
        <div className="p-5">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                {detail.id}
                {detail.isSimulated && (
                  <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-800 text-xs font-bold">DEMO / SIMULATED</span>
                )}
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${STATUS_CLASS(detail.status)}`}>{detail.status}</span>
                {detail.isEmergency && (
                  <span
                    className="px-2 py-0.5 rounded bg-red-100 text-red-800 text-xs font-bold"
                    title="The caller pressed 0 (emergency). Clinical risk is decided by triage, not by this keypress."
                  >
                    CALLER REPORTED EMERGENCY
                  </span>
                )}
                {riskPill(detail.triageRiskLevel)}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {detail.farmerName || "Unknown caller"} · {detail.callerPhone || "—"} {detail.callerMasked ? "(masked)" : ""} ·{" "}
                {detail.village || "—"}
                {detail.district ? `, ${detail.district}` : ""} · {detail.language || "—"} · started {time(detail.startedAt)}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                Channel: IVR ({detail.provider}) · Call ID {detail.callSid}
                {detail.ivrMenuOption ? ` · Menu: ${MENU_LABEL[detail.ivrMenuOption] || detail.ivrMenuOption}` : ""}
              </p>
            </div>
            <button onClick={() => setDetail(null)} className="text-gray-400 hover:text-gray-700"><X size={20} /></button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">
            <div className="bg-gray-50 rounded-lg p-3"><div className="text-gray-500 text-xs">Species</div><div className="font-medium">{detail.species || "Unknown"}</div></div>
            <div className="bg-gray-50 rounded-lg p-3"><div className="text-gray-500 text-xs">Affected</div><div className="font-medium">{detail.numberAffected ?? "—"}</div></div>
            <div className="bg-gray-50 rounded-lg p-3"><div className="text-gray-500 text-xs">Report</div><div className="font-medium">{detail.reportNumber || "—"}</div></div>
            <div className="bg-gray-50 rounded-lg p-3"><div className="text-gray-500 text-xs">Callback</div><div className="font-medium">{detail.callback ? `${detail.callback.priority} · ${detail.callback.status}` : "—"}</div></div>
          </div>

          {detail.symptoms && detail.symptoms.length > 0 && (
            <p className="text-sm text-gray-700 mb-3"><span className="text-gray-500">Symptoms:</span> {detail.symptoms.join(", ")}</p>
          )}

          {detail.answers.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-1">IVR Survey Answers</h4>
              <table className="w-full text-xs text-left">
                <tbody className="divide-y divide-gray-100">
                  {detail.answers.map((a) => (
                    <tr key={a.question}>
                      <td className="py-1 pr-3 text-gray-500">{a.question}</td>
                      <td className="py-1 font-mono">{JSON.stringify(a.normalized ?? a.answer)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {detail.transcript && detail.transcript.segments.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-1">Transcript</h4>
              <div className="bg-gray-50 rounded-lg p-3 text-xs space-y-1 max-h-40 overflow-y-auto">
                {detail.transcript.segments.map((s) => (
                  <p key={s.id}><span className="font-bold text-gray-600">{s.speaker}:</span> {s.text}</p>
                ))}
              </div>
            </div>
          )}

          {detail.aiSummary && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-1">AI / Template Summary</h4>
              <pre className="bg-blue-50 rounded-lg p-3 text-xs whitespace-pre-wrap max-h-48 overflow-y-auto">{detail.aiSummary}</pre>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => (window.location.href = "/reporting")}
              className="px-3 py-2 bg-brandBlue text-white rounded-lg text-sm font-medium hover:opacity-90"
            >
              Create Report
            </button>
            <button
              onClick={() => (window.location.href = "/surveillance")}
              className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50"
              disabled={!detail.reportId}
            >
              View Report
            </button>
            {detail.callback && detail.callback.status === "PENDING" && (
              <button onClick={() => callbackAction(detail.callback!.id, "accept")} className="px-3 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">
                Accept Callback
              </button>
            )}
            <a
              href={detail.callerPhone && !detail.callerMasked ? `tel:${detail.callerPhone}` : undefined}
              className={`px-3 py-2 rounded-lg text-sm font-medium border ${
                detail.callerPhone && !detail.callerMasked
                  ? "bg-white border-gray-300 hover:bg-gray-50"
                  : "bg-gray-100 border-gray-200 text-gray-400 pointer-events-none"
              }`}
              title={detail.callerMasked ? "Phone masked for your role" : "Call farmer"}
            >
              Call Farmer
            </a>
            {detail.isActive && (
              <button onClick={() => closeCall(detail.id)} className="px-3 py-2 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm font-medium hover:bg-red-100">
                Close
              </button>
            )}
          </div>
        </div>
      ) : sub === "callbacks" ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm min-w-[720px]">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Farmer</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Species</th>
                <th className="px-4 py-3">Symptoms</th>
                <th className="px-4 py-3">Call time</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {callbacks.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${PRIORITY_CLASS[c.priority] || "bg-gray-100"}`}>{c.priority}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{c.callerPhone || "—"}</div>
                    {c.isSimulated && <span className="text-[10px] font-bold text-purple-700">DEMO / SIMULATED</span>}
                  </td>
                  <td className="px-4 py-3">{[c.village, c.taluka, c.district].filter(Boolean).join(", ") || "Unknown"}</td>
                  <td className="px-4 py-3">{c.species || "—"}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-[180px] truncate">{c.symptoms.join(", ") || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{time(c.callTime)}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-bold ${STATUS_CLASS(c.status)}`}>{c.status}</span></td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {c.status === "PENDING" && (
                        <button onClick={() => callbackAction(c.id, "accept")} className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs font-medium hover:bg-green-100">Accept</button>
                      )}
                      {c.status !== "COMPLETED" && c.status !== "CANCELLED" && (
                        <>
                          <button onClick={() => callbackAction(c.id, "call-back")} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium hover:bg-blue-100">Call back</button>
                          {c.reportId && (
                            <button onClick={() => callbackAction(c.id, "create-case")} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs font-medium hover:bg-indigo-100">Create case</button>
                          )}
                          <button onClick={() => callbackAction(c.id, "complete")} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium hover:bg-gray-200">Mark completed</button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {callbacks.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No callback requests.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm min-w-[680px]">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Call</th>
                <th className="px-4 py-3">Channel</th>
                <th className="px-4 py-3">Farmer</th>
                <th className="px-4 py-3">Language</th>
                <th className="px-4 py-3">District</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Report</th>
                <th className="px-4 py-3">Started</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {calls.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => openDetail(c.id)}>
                  <td className="px-4 py-3 font-medium">
                    <div className="flex items-center gap-2">
                      {c.status === "FAILED" ? <PhoneOff size={14} className="text-red-500" /> : <Phone size={14} className="text-green-600" />}
                      {c.id}
                    </div>
                    {c.isSimulated && <span className="text-[10px] font-bold text-purple-700 ml-6">{c.demoLabel}</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    IVR · {c.provider}
                    {c.ivrMenuOption && (
                      <div className="text-[10px] text-gray-400">{MENU_LABEL[c.ivrMenuOption] || c.ivrMenuOption}</div>
                    )}
                    {c.isEmergency && <div className="text-[10px] font-bold text-red-600">EMERGENCY</div>}
                  </td>
                  <td className="px-4 py-3">{c.callerPhone || "—"}</td>
                  <td className="px-4 py-3">{c.language || "—"}</td>
                  <td className="px-4 py-3">{c.district || "Unknown"}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-bold ${STATUS_CLASS(c.status)}`}>{c.status}</span></td>
                  <td className="px-4 py-3 text-gray-500">{c.reportId ? c.reportId.slice(0, 14) + "…" : "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{time(c.startedAt)}</td>
                  <td className="px-4 py-3 text-brandBlue"><ChevronRight size={16} /></td>
                </tr>
              ))}
              {calls.length === 0 && (
                <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No {sub === "active" ? "active" : ""} calls.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
