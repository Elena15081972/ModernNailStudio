export interface Service {
  name: string;
  category: string | null;
  price: string | null;
  durationMinutes: string | null;
}

export interface StaffMember {
  name: string;
  role: string | null;
}

export interface Client {
  name: string;
  phone: string | null;
}

export interface Appointment {
  time: string;
  clientName: string;
  service: string;
  staffName: string;
}

export interface CreateAppointmentInput {
  date: string; // YYYY-MM-DD
  time: string; // HH:mm
  serviceName: string;
  staffName: string;
  clientName: string;
  clientPhone: string;
}

export interface CreateAppointmentResult {
  success: boolean;
  message: string;
}
