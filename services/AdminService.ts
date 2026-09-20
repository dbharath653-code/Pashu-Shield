export interface AdminUser {
  id: string;
  name: string;
  email: string;
  phone: string;
  role: string;
  department: string;
  district: string;
  status: "Active" | "Inactive" | "Pending";
  lastLogin: string;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user: string;
  role: string;
  action: string;
  module: string;
  description: string;
  ip: string;
  result: "Success" | "Failed";
}

export interface ApprovalRequest {
  id: string;
  type: "User" | "Role" | "Facility" | "Config";
  requester: string;
  date: string;
  details: string;
  status: "Pending" | "Approved" | "Rejected";
}

export interface Facility {
  id: string;
  name: string;
  type: string;
  district: string;
  taluka: string;
  status: "Active" | "Inactive";
  contact: string;
}

export const AdminService = {
  async getOverview() {
    await new Promise(r => setTimeout(r, 400));
    return {
      totalUsers: 1245,
      activeUsers: 1120,
      pendingApprovals: 12,
      fieldOfficers: 450,
      veterinarians: 320,
      labs: 45,
      districts: 36,
      systemAlerts: 3,
      recentActivity: [
        { id: 1, action: "User created", details: "Rahul Deshmukh (Vet Officer)", time: "10 mins ago" },
        { id: 2, action: "Permission updated", details: "State Admin updated Lab Officer role", time: "1 hour ago" },
        { id: 3, action: "Account activated", details: "Priya Patil (Field Officer)", time: "2 hours ago" },
        { id: 4, action: "Configuration changed", details: "SMS Notification threshold updated", time: "5 hours ago" }
      ]
    };
  },

  async getUsers(): Promise<AdminUser[]> {
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch("/api/v1/users", {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.map((u: any) => ({
            id: u.id,
            name: u.full_name,
            email: u.email,
            phone: u.phone || "+91 9823000000",
            role: u.role,
            department: u.department || "Animal Husbandry",
            district: u.district || "Pune",
            status: u.is_active !== false ? "Active" : "Inactive",
            lastLogin: "Active Today"
          }));
        }
      }
    } catch {
      // Fallback below
    }

    return [
      { id: "EMP-1001", name: "Dr. Sunil Patil", email: "sunil.patil@mah.gov.in", phone: "+91 9876543210", role: "District Administrator", department: "Animal Husbandry", district: "Pune", status: "Active", lastLogin: "2026-09-10 14:30" },
      { id: "EMP-1002", name: "Priya Sharma", email: "priya.s@mah.gov.in", phone: "+91 9876543211", role: "Field Veterinary Officer", department: "Disease Control", district: "Nashik", status: "Active", lastLogin: "2026-09-10 09:15" },
      { id: "EMP-1003", name: "Amit Joshi", email: "amit.j@mah.gov.in", phone: "+91 9876543212", role: "Lab Officer", department: "Diagnostics", district: "Nagpur", status: "Inactive", lastLogin: "2026-09-01 11:20" },
      { id: "EMP-1004", name: "Ramesh Pawar", email: "ramesh.p@mah.gov.in", phone: "+91 9876543213", role: "Data Entry Operator", department: "Admin", district: "Mumbai", status: "Pending", lastLogin: "Never" },
      { id: "EMP-1005", name: "Dr. Anjali Deshmukh", email: "anjali.d@mah.gov.in", phone: "+91 9876543214", role: "State Administrator", department: "Headquarters", district: "Maharashtra", status: "Active", lastLogin: "2026-09-10 18:45" },
    ];
  },

  async getAuditLogs(): Promise<AuditLogEntry[]> {
    try {
      const token = localStorage.getItem("auth_token");
      const res = await fetch("/api/v1/audit/logs", {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) return data;
      }
    } catch {
      // Fallback below
    }

    return [
      { id: "AL-592", timestamp: "2026-09-20 05:12:22", user: "Dr. Sunil Patil", role: "District Administrator", action: "UPDATE", module: "Vaccination", description: "Updated vaccination threshold for Pune", ip: "10.23.45.12", result: "Success" },
      { id: "AL-591", timestamp: "2026-09-20 04:45:10", user: "Priya Sharma", role: "Field Veterinary Officer", action: "CREATE", module: "Case Reporting", description: "Created disease case #CR-992", ip: "192.168.1.5", result: "Success" },
      { id: "AL-590", timestamp: "2026-09-20 03:30:05", user: "Amit Joshi", role: "Lab Officer", action: "LOGIN", module: "Auth", description: "Verified lab batch result SMP-10231", ip: "114.143.2.1", result: "Success" },
      { id: "AL-589", timestamp: "2026-09-20 02:15:00", user: "Dr. Anjali Deshmukh", role: "State Administrator", action: "ACTIVATE", module: "User Management", description: "Activated user account EMP-1001", ip: "10.0.0.1", result: "Success" },
    ];
  },

  async getApprovals(): Promise<ApprovalRequest[]> {
    await new Promise(r => setTimeout(r, 300));
    return [
      { id: "REQ-001", type: "User", requester: "Ramesh Pawar", date: "2026-09-10", details: "New account creation request for Data Entry Operator in Mumbai.", status: "Pending" },
      { id: "REQ-002", type: "Role", requester: "Dr. Sunil Patil", date: "2026-09-09", details: "Request to upgrade Priya Sharma to District Admin.", status: "Pending" },
      { id: "REQ-003", type: "Facility", requester: "Nagpur HQ", date: "2026-09-08", details: "Register new Diagnostic Lab in Wardha.", status: "Pending" },
    ];
  },

  async getFacilities(): Promise<Facility[]> {
    await new Promise(r => setTimeout(r, 300));
    return [
      { id: "FAC-001", name: "Pune Central Veterinary Hospital", type: "Veterinary Hospital", district: "Pune", taluka: "Haveli", status: "Active", contact: "020-25678901" },
      { id: "FAC-002", name: "Nashik Regional Diagnostic Lab", type: "Diagnostic Laboratory", district: "Nashik", taluka: "Nashik", status: "Active", contact: "0253-2345678" },
      { id: "FAC-003", name: "Nagpur Government Farm", type: "Government Farm", district: "Nagpur", taluka: "Nagpur Rural", status: "Inactive", contact: "0712-2564321" },
    ];
  }
};
