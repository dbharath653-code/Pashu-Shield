
export default function RoleManagement() {
  const roles = ["State Administrator", "District Administrator", "Veterinary Officer", "Lab Officer", "Read Only"];
  const modules = ["Dashboard", "Disease Surveillance", "Case Reporting", "Lab Management", "Vaccination", "Administration"];
  const permissions = ["View", "Create", "Edit", "Delete", "Approve", "Export"];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-10rem)] overflow-hidden">
       <div className="p-5 border-b border-gray-200 bg-gray-50">
          <h3 className="text-lg font-bold text-gray-900">Role & Permission Matrix</h3>
          <p className="text-sm text-gray-500">Configure access levels for each system role.</p>
       </div>

       <div className="flex-1 overflow-auto p-5">
          <div className="flex gap-4 mb-6">
             <div className="w-64 shrink-0">
                <label className="block text-sm font-medium text-gray-700 mb-2">Select Role to Edit</label>
                <select className="w-full border border-gray-300 rounded-lg p-2 focus:ring-brandBlue focus:border-brandBlue">
                   {roles.map(r => <option key={r}>{r}</option>)}
                </select>
             </div>
             <div className="self-end pb-1">
                <button className="px-4 py-2 bg-brandBlue text-white font-medium rounded-lg hover:bg-blue-700">Save Permissions</button>
             </div>
          </div>

          <table className="w-full text-left text-sm whitespace-nowrap border-collapse border border-gray-200">
             <thead className="bg-gray-100 text-gray-700">
                <tr>
                   <th className="p-3 border border-gray-200">Module</th>
                   {permissions.map(p => <th key={p} className="p-3 border border-gray-200 text-center">{p}</th>)}
                </tr>
             </thead>
             <tbody>
                {modules.map(mod => (
                   <tr key={mod} className="hover:bg-gray-50">
                      <td className="p-3 border border-gray-200 font-medium text-gray-900">{mod}</td>
                      {permissions.map(p => (
                         <td key={p} className="p-3 border border-gray-200 text-center">
                            <input type="checkbox" className="w-4 h-4 text-brandBlue rounded focus:ring-brandBlue" defaultChecked={Math.random() > 0.3} />
                         </td>
                      ))}
                   </tr>
                ))}
             </tbody>
          </table>
       </div>
    </div>
  );
}
