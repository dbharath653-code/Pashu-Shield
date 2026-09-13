import React, { useState, useEffect } from "react";
import { AdminService } from "../../services/AdminService";
import type { AdminUser } from "../../services/AdminService";
import { Search, Plus, MoreVertical, Edit, ShieldBan, ShieldCheck, Key } from "lucide-react";

export default function UserManagement() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    AdminService.getUsers().then(res => {
      setUsers(res);
      setLoading(false);
    });
  }, []);

  const filtered = users.filter(u => u.name.toLowerCase().includes(search.toLowerCase()) || u.id.toLowerCase().includes(search.toLowerCase()));

  const handleAction = (action: string, id: string) => {
     alert(action + " action triggered for user " + id);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-10rem)]">
       <div className="p-5 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-gray-50 rounded-t-xl">
          <h3 className="text-lg font-bold text-gray-900">User Management</h3>
          
          <div className="flex items-center gap-3 w-full sm:w-auto">
             <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                <input 
                  type="text" 
                  placeholder="Search users..." 
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-brandBlue focus:border-brandBlue"
                />
             </div>
             <button onClick={() => setShowAddModal(true)} className="px-4 py-2 bg-brandBlue text-white font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2 whitespace-nowrap">
                <Plus size={18} /> Add User
             </button>
          </div>
       </div>

       <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
             <thead className="bg-gray-100 text-gray-600 font-medium sticky top-0 shadow-sm z-10">
                <tr>
                   <th className="px-6 py-4">Name & ID</th>
                   <th className="px-6 py-4">Role</th>
                   <th className="px-6 py-4">District</th>
                   <th className="px-6 py-4">Contact</th>
                   <th className="px-6 py-4">Status</th>
                   <th className="px-6 py-4 text-right">Actions</th>
                </tr>
             </thead>
             <tbody className="divide-y divide-gray-100">
                {loading ? (
                   <tr><td colSpan={6} className="text-center p-8 text-gray-500">Loading users...</td></tr>
                ) : filtered.length > 0 ? filtered.map(user => (
                   <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                         <div className="font-bold text-gray-900">{user.name}</div>
                         <div className="text-xs text-gray-500">{user.id}</div>
                      </td>
                      <td className="px-6 py-4">
                         <div className="text-gray-900">{user.role}</div>
                         <div className="text-xs text-gray-500">{user.department}</div>
                      </td>
                      <td className="px-6 py-4 text-gray-700">{user.district}</td>
                      <td className="px-6 py-4">
                         <div className="text-gray-900">{user.phone}</div>
                         <div className="text-xs text-gray-500">{user.email}</div>
                      </td>
                      <td className="px-6 py-4">
                         <span className={`px-2 py-1 text-xs font-bold rounded-full ${user.status === "Active" ? "bg-green-100 text-green-800" : user.status === "Inactive" ? "bg-red-100 text-red-800" : "bg-orange-100 text-orange-800"}`}>
                            {user.status}
                         </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                         <div className="flex items-center justify-end gap-2">
                            <button onClick={() => handleAction("Edit", user.id)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg" title="Edit"><Edit size={16}/></button>
                            <button onClick={() => handleAction("Reset Password", user.id)} className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg" title="Reset Password"><Key size={16}/></button>
                            {user.status === "Active" ? (
                               <button onClick={() => handleAction("Deactivate", user.id)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg" title="Deactivate"><ShieldBan size={16}/></button>
                            ) : (
                               <button onClick={() => handleAction("Activate", user.id)} className="p-2 text-green-600 hover:bg-green-50 rounded-lg" title="Activate"><ShieldCheck size={16}/></button>
                            )}
                         </div>
                      </td>
                   </tr>
                )) : (
                   <tr><td colSpan={6} className="text-center p-8 text-gray-500">No users found.</td></tr>
                )}
             </tbody>
          </table>
       </div>

       {showAddModal && (
          <div className="fixed inset-0 bg-black/50 z-50 flex justify-center items-center p-4">
             <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden">
                <div className="bg-brandBlue text-white p-5 flex justify-between items-center">
                   <h3 className="text-lg font-bold">Add New User</h3>
                   <button onClick={() => setShowAddModal(false)} className="text-white/80 hover:text-white">✕</button>
                </div>
                <div className="p-6 grid grid-cols-2 gap-4">
                   <div>
                      <label className="block text-sm text-gray-700 mb-1">Full Name</label>
                      <input type="text" className="w-full border border-gray-300 rounded p-2" />
                   </div>
                   <div>
                      <label className="block text-sm text-gray-700 mb-1">Employee ID</label>
                      <input type="text" className="w-full border border-gray-300 rounded p-2" />
                   </div>
                   <div>
                      <label className="block text-sm text-gray-700 mb-1">Email</label>
                      <input type="email" className="w-full border border-gray-300 rounded p-2" />
                   </div>
                   <div>
                      <label className="block text-sm text-gray-700 mb-1">Mobile</label>
                      <input type="tel" className="w-full border border-gray-300 rounded p-2" />
                   </div>
                   <div>
                      <label className="block text-sm text-gray-700 mb-1">Role</label>
                      <select className="w-full border border-gray-300 rounded p-2">
                         <option>State Administrator</option>
                         <option>District Administrator</option>
                         <option>Veterinary Officer</option>
                         <option>Lab Officer</option>
                      </select>
                   </div>
                   <div>
                      <label className="block text-sm text-gray-700 mb-1">District</label>
                      <select className="w-full border border-gray-300 rounded p-2">
                         <option>Pune</option>
                         <option>Nashik</option>
                      </select>
                   </div>
                </div>
                <div className="p-5 border-t border-gray-200 flex justify-end gap-3 bg-gray-50">
                   <button onClick={() => setShowAddModal(false)} className="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
                   <button onClick={() => { alert("User added"); setShowAddModal(false); }} className="px-4 py-2 bg-brandBlue text-white rounded-lg hover:bg-blue-700">Save User</button>
                </div>
             </div>
          </div>
       )}
    </div>
  );
}
