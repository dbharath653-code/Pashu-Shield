import { useState } from "react";
import { useLab } from "../../context/LabContext";
import type { LabSample, LabTest } from "../../context/LabContext";
import { ArrowLeft, QrCode, FileText, CheckCircle, Plus, AlertTriangle } from "lucide-react";

export default function SampleDetails({ sample, onBack }: { sample: LabSample, onBack: () => void }) {
  const { updateSample } = useLab();
  const [activeTab, setActiveTab] = useState("Overview");
  
  // Test entry form
  const [newTest, setNewTest] = useState({ testName: "" });
  const [resultEntry, setResultEntry] = useState<{ [key: string]: { result: "Negative" | "Positive" | "Inconclusive" | "Invalid", value: string, remarks: string } }>({});

  const handleStatusChange = async (newStatus: LabSample["status"]) => {
    await updateSample({ ...sample, status: newStatus });
  };

  const handleAddTest = async () => {
    if (!newTest.testName) return;
    const test: LabTest = { id: `T-${Date.now()}`, testName: newTest.testName, status: "Pending" };
    await updateSample({ ...sample, tests: [...sample.tests, test], status: "Testing" });
    setNewTest({ testName: "" });
  };

  const handleSaveResult = async (testId: string) => {
    const entry = resultEntry[testId];
    if (!entry || !entry.result) return;
    
    const updatedTests = sample.tests.map(t => {
      if (t.id === testId) {
        return { ...t, status: "Completed" as const, result: entry.result, value: entry.value, remarks: entry.remarks };
      }
      return t;
    });

    const allCompleted = updatedTests.every(t => t.status === "Completed");
    await updateSample({ 
      ...sample, 
      tests: updatedTests, 
      status: allCompleted ? "Result Pending" : "Testing" 
    });
  };

  const handleVerifyResult = async () => {
    await updateSample({
      ...sample,
      status: "Verified",
      verification: {
        verifiedBy: "Dr. Lab Officer",
        date: new Date().toISOString(),
        remarks: "Approved for release."
      }
    });
    alert("Results Verified! Alerts have been dispatched to Disease Surveillance.");
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
            <ArrowLeft size={20} />
          </button>
          <div>
             <h2 className="text-xl font-bold text-gray-900">SAMPLE: {sample.id}</h2>
             <span className={`px-2 py-0.5 inline-flex text-xs leading-5 font-bold rounded-full mt-1
                    ${sample.priority === "Critical" ? "bg-red-100 text-red-800" : 
                      sample.priority === "Urgent" ? "bg-orange-100 text-orange-800" : 
                      "bg-gray-100 text-gray-800"}`}>
                    {sample.priority} PRIORITY
             </span>
             <span className="ml-2 text-sm text-gray-500 font-medium">Status: {sample.status}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => { alert("Sending sample barcode to connected label printer..."); window.print(); }} className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium flex items-center gap-1">
             <QrCode size={16} /> Print Label
          </button>

          {sample.status === "Collected" && (
            <button onClick={() => handleStatusChange("In Transit")} className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 text-sm font-medium">
              Dispatch
            </button>
          )}
          {["Collected", "In Transit"].includes(sample.status) && (
            <button onClick={() => handleStatusChange("Received")} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium">
              Receive at Lab
            </button>
          )}
          {sample.status === "Received" && (
            <div className="flex gap-2">
               <button onClick={() => handleStatusChange("Rejected")} className="px-4 py-2 bg-red-100 text-red-800 rounded-lg hover:bg-red-200 text-sm font-medium">
                 Reject
               </button>
               <button onClick={() => handleStatusChange("Accepted")} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm font-medium">
                 Accept Sample
               </button>
            </div>
          )}
          {sample.status === "Result Pending" && (
            <button onClick={handleVerifyResult} className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium flex items-center gap-2">
              <CheckCircle size={16} /> Verify Results
            </button>
          )}
        </div>
      </div>

      <div className="p-6 grid grid-cols-3 gap-6">
         <div className="col-span-1 space-y-6">
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 flex flex-col items-center text-center">
               <QrCode size={96} className="text-gray-800 mb-2" />
               <p className="font-mono font-bold text-lg">{sample.id}</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
               <h3 className="font-semibold mb-3 flex items-center gap-2"><FileText size={16}/> Case Information</h3>
               <div className="space-y-2 text-sm">
                  <p><span className="text-gray-500">Case ID:</span> {sample.caseId || "N/A"}</p>
                  <p><span className="text-gray-500">Animal/Herd ID:</span> {sample.animalId || "N/A"}</p>
                  <p><span className="text-gray-500">Species:</span> {sample.species}</p>
                  <p><span className="text-gray-500">Sample Type:</span> {sample.sampleType}</p>
                  <p><span className="text-gray-500">Suspected Disease:</span> <span className="font-medium text-orange-700">{sample.diseaseSuspected}</span></p>
                  <p className="pt-2 border-t border-gray-100"><span className="text-gray-500">Collected:</span> {new Date(sample.collectionDate).toLocaleString()}</p>
                  <p><span className="text-gray-500">Location:</span> {sample.location}, {sample.district}</p>
               </div>
            </div>
         </div>

         <div className="col-span-2">
            <div className="flex border-b border-gray-200 mb-4">
               {["Overview", "Tests & Results", "Verification", "Disease Impact"].map(tab => (
                 <button key={tab} onClick={() => setActiveTab(tab)} className={`py-2 px-4 text-sm font-medium border-b-2 ${activeTab === tab ? "border-brandBlue text-brandBlue" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
                   {tab}
                 </button>
               ))}
            </div>

            {activeTab === "Overview" && (
               <div className="space-y-4">
                 <h3 className="font-semibold text-gray-800">Chain of Custody Timeline</h3>
                 <div className="border-l-2 border-brandBlue pl-4 space-y-4 py-2">
                    <div className="relative">
                       <div className="absolute -left-[21px] top-1 w-3 h-3 bg-brandBlue rounded-full border-2 border-white"></div>
                       <p className="text-sm font-medium text-brandBlue">Collected</p>
                       <p className="text-xs text-gray-500">{new Date(sample.collectionDate).toLocaleString()}</p>
                    </div>
                    {["In Transit", "Received", "Accepted", "Testing", "Result Pending", "Verified"].includes(sample.status) && (
                      <div className="relative">
                         <div className="absolute -left-[21px] top-1 w-3 h-3 bg-blue-500 rounded-full border-2 border-white"></div>
                         <p className="text-sm font-medium">Sample Received & Accepted</p>
                      </div>
                    )}
                    {sample.status === "Verified" && (
                      <div className="relative">
                         <div className="absolute -left-[21px] top-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                         <p className="text-sm font-medium text-green-700">Results Verified & Finalized</p>
                         <p className="text-xs text-gray-500">{sample.verification?.date ? new Date(sample.verification.date).toLocaleString() : ""}</p>
                      </div>
                    )}
                 </div>
               </div>
            )}

            {activeTab === "Tests & Results" && (
               <div className="space-y-6">
                 {["Accepted", "Testing", "Result Pending"].includes(sample.status) && (
                    <div className="flex gap-2 items-end bg-blue-50 p-4 rounded-lg border border-blue-100">
                       <div className="flex-1">
                          <label className="block text-sm font-medium text-gray-700 mb-1">Assign New Test</label>
                          <input type="text" value={newTest.testName} onChange={e => setNewTest({ testName: e.target.value })} className="w-full border-gray-300 rounded-md p-2 border" placeholder="e.g. FMD RT-PCR" />
                       </div>
                       <button onClick={handleAddTest} className="px-4 py-2 bg-brandBlue text-white rounded-lg flex items-center gap-2 text-sm font-medium">
                          <Plus size={16} /> Assign Test
                       </button>
                    </div>
                 )}

                 <div className="space-y-4">
                    {sample.tests.length === 0 ? (
                       <p className="text-gray-500 text-sm">No tests assigned yet.</p>
                    ) : (
                       sample.tests.map(test => (
                          <div key={test.id} className="border border-gray-200 rounded-xl p-4 bg-white shadow-sm">
                             <div className="flex justify-between items-center mb-3">
                                <h4 className="font-bold text-gray-900">{test.testName}</h4>
                                <span className="text-xs font-bold px-2 py-1 bg-gray-100 rounded-full">{test.status}</span>
                             </div>
                             
                             {test.status === "Completed" ? (
                                <div className="grid grid-cols-3 gap-4 bg-gray-50 p-3 rounded-lg border border-gray-100">
                                   <div>
                                      <p className="text-xs text-gray-500">Result</p>
                                      <p className={`font-bold ${test.result === "Positive" ? "text-red-600" : "text-green-600"}`}>{test.result}</p>
                                   </div>
                                   <div>
                                      <p className="text-xs text-gray-500">Value (e.g. Ct)</p>
                                      <p className="font-medium text-gray-900">{test.value || "N/A"}</p>
                                   </div>
                                   <div>
                                      <p className="text-xs text-gray-500">Remarks</p>
                                      <p className="font-medium text-gray-900">{test.remarks || "None"}</p>
                                   </div>
                                </div>
                             ) : (
                                <div className="grid grid-cols-4 gap-2 items-end">
                                   <div className="col-span-1">
                                      <label className="block text-xs font-medium text-gray-700 mb-1">Result</label>
                                      <select 
                                        className="w-full border border-gray-300 rounded p-1.5 text-sm"
                                        onChange={(e) => setResultEntry({ ...resultEntry, [test.id]: { ...resultEntry[test.id], result: e.target.value as any } })}
                                      >
                                         <option value="">Select...</option>
                                         <option value="Negative">Negative</option>
                                         <option value="Positive">Positive</option>
                                         <option value="Inconclusive">Inconclusive</option>
                                         <option value="Invalid">Invalid</option>
                                      </select>
                                   </div>
                                   <div className="col-span-1">
                                      <label className="block text-xs font-medium text-gray-700 mb-1">Value/Ct</label>
                                      <input type="text" onChange={(e) => setResultEntry({ ...resultEntry, [test.id]: { ...resultEntry[test.id], value: e.target.value } })} className="w-full border border-gray-300 rounded p-1.5 text-sm" placeholder="e.g. 24.6" />
                                   </div>
                                   <div className="col-span-1">
                                      <label className="block text-xs font-medium text-gray-700 mb-1">Interpretation</label>
                                      <input type="text" onChange={(e) => setResultEntry({ ...resultEntry, [test.id]: { ...resultEntry[test.id], remarks: e.target.value } })} className="w-full border border-gray-300 rounded p-1.5 text-sm" placeholder="Notes" />
                                   </div>
                                   <div className="col-span-1">
                                      <button onClick={() => handleSaveResult(test.id)} className="w-full px-2 py-1.5 bg-brandBlue text-white rounded text-sm font-medium">Save</button>
                                   </div>
                                </div>
                             )}
                          </div>
                       ))
                    )}
                 </div>
               </div>
            )}

            {activeTab === "Verification" && (
               <div className="bg-gray-50 p-6 rounded-xl border border-gray-200 text-center">
                  {sample.status === "Verified" ? (
                     <div>
                        <CheckCircle size={48} className="mx-auto text-green-500 mb-3" />
                        <h3 className="text-xl font-bold text-gray-900">Results Verified</h3>
                        <p className="text-sm text-gray-500 mt-2">Verified by: {sample.verification?.verifiedBy}</p>
                        <p className="text-sm text-gray-500">Date: {new Date(sample.verification?.date || "").toLocaleString()}</p>
                        <p className="text-sm text-gray-700 mt-4 italic">"{sample.verification?.remarks}"</p>
                     </div>
                  ) : sample.status === "Result Pending" ? (
                     <div>
                        <p className="text-gray-600 mb-4">All tests are completed. Awaiting Lab Officer verification.</p>
                        <button onClick={handleVerifyResult} className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium flex items-center gap-2 mx-auto">
                           <CheckCircle size={18} /> Approve & Publish Results
                        </button>
                     </div>
                  ) : (
                     <p className="text-gray-500">Testing must be completed before verification.</p>
                  )}
               </div>
            )}

            {activeTab === "Disease Impact" && (
               <div className="space-y-4">
                  {sample.tests.some(t => t.result === "Positive") && sample.status === "Verified" ? (
                     <div className="bg-red-50 border border-red-200 rounded-xl p-6">
                        <div className="flex items-center gap-3 text-red-800 mb-4">
                           <AlertTriangle size={24} />
                           <h3 className="text-xl font-bold">Confirmed Positive Result</h3>
                        </div>
                        <p className="text-red-700 mb-4">This laboratory result has automatically updated the linked Case, Animal, and Herd profiles. Alerts have been pushed to Disease Surveillance and the GIS Risk Map.</p>
                        <div className="flex gap-3">
                           <button onClick={() => alert("Opening Case Profile...")} className="px-4 py-2 bg-white text-red-700 border border-red-200 rounded-lg text-sm font-medium hover:bg-red-100">View Case Report</button>
                           <button onClick={() => alert("Opening GIS Map...")} className="px-4 py-2 bg-red-700 text-white rounded-lg text-sm font-medium hover:bg-red-800">View on Risk Map</button>
                        </div>
                     </div>
                  ) : (
                     <div className="p-6 border border-gray-200 rounded-xl bg-gray-50 text-center">
                        <p className="text-gray-500">No positive verified results present. No automated disease surveillance triggers executed.</p>
                     </div>
                  )}
               </div>
            )}
         </div>
      </div>
    </div>
  );
}

