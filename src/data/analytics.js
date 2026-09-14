export const hourlyTraffic = [
  { hour: "00:00", pedestrians: 12, vehicles: 34, incidents: 0 },
  { hour: "01:00", pedestrians: 5, vehicles: 18, incidents: 0 },
  { hour: "02:00", pedestrians: 2, vehicles: 11, incidents: 0 },
  { hour: "03:00", pedestrians: 1, vehicles: 8, incidents: 0 },
  { hour: "04:00", pedestrians: 3, vehicles: 14, incidents: 0 },
  { hour: "05:00", pedestrians: 15, vehicles: 42, incidents: 0 },
  { hour: "06:00", pedestrians: 45, vehicles: 120, incidents: 1 },
  { hour: "07:00", pedestrians: 112, vehicles: 285, incidents: 2 },
  { hour: "08:00", pedestrians: 187, vehicles: 342, incidents: 3 },
  { hour: "09:00", pedestrians: 164, vehicles: 308, incidents: 2 },
  { hour: "10:00", pedestrians: 142, vehicles: 264, incidents: 1 },
  { hour: "11:00", pedestrians: 156, vehicles: 278, incidents: 2 },
  { hour: "12:00", pedestrians: 198, vehicles: 290, incidents: 4 },
  { hour: "13:00", pedestrians: 175, vehicles: 268, incidents: 2 },
  { hour: "14:00", pedestrians: 162, vehicles: 252, incidents: 1 },
  { hour: "15:00", pedestrians: 178, vehicles: 274, incidents: 3 },
  { hour: "16:00", pedestrians: 205, vehicles: 312, incidents: 4 },
  { hour: "17:00", pedestrians: 238, vehicles: 368, incidents: 5 },
  { hour: "18:00", pedestrians: 210, vehicles: 330, incidents: 3 },
  { hour: "19:00", pedestrians: 168, vehicles: 245, incidents: 6 },
  { hour: "20:00", pedestrians: 124, vehicles: 198, incidents: 3 },
  { hour: "21:00", pedestrians: 82, vehicles: 142, incidents: 2 },
  { hour: "22:00", pedestrians: 48, vehicles: 86, incidents: 1 },
  { hour: "23:00", pedestrians: 24, vehicles: 52, incidents: 0 },
];

export const weeklyTrend = [
  { day: "Mon", detections: 342, incidents: 12, resolved: 10 },
  { day: "Tue", detections: 418, incidents: 15, resolved: 14 },
  { day: "Wed", detections: 387, incidents: 11, resolved: 11 },
  { day: "Thu", detections: 456, incidents: 18, resolved: 15 },
  { day: "Fri", detections: 523, incidents: 22, resolved: 19 },
  { day: "Sat", detections: 612, incidents: 26, resolved: 23 },
  { day: "Sun", detections: 489, incidents: 19, resolved: 18 },
];

export const topEventTypes = [
  { type: "Person Detection", count: 1247 },
  { type: "Vehicle Classification", count: 892 },
  { type: "Speed Measurement", count: 534 },
  { type: "Crowd Density Alert", count: 312 },
  { type: "Intrusion Detection", count: 187 },
  { type: "Abandoned Object", count: 94 },
  { type: "Loitering Alert", count: 78 },
  { type: "Wrong Way Detection", count: 45 },
  { type: "Facial Recognition Match", count: 38 },
  { type: "ANPR Plate Read", count: 1560 },
];

export const cameraUtilization = [
  { cameraId: "CAM-01", utilization: 88.4, uptime: 99.9 },
  { cameraId: "CAM-02", utilization: 62.1, uptime: 98.7 },
  { cameraId: "CAM-03", utilization: 91.7, uptime: 99.8 },
  { cameraId: "CAM-04", utilization: 96.3, uptime: 100.0 },
  { cameraId: "CAM-05", utilization: 84.9, uptime: 99.5 },
  { cameraId: "CAM-06", utilization: 71.2, uptime: 99.1 },
  { cameraId: "CAM-07", utilization: 94.2, uptime: 99.8 },
  { cameraId: "CAM-08", utilization: 89.6, uptime: 98.3 },
  { cameraId: "CAM-09", utilization: 76.8, uptime: 94.2 },
  { cameraId: "CAM-10", utilization: 82.5, uptime: 99.0 },
  { cameraId: "CAM-12", utilization: 97.1, uptime: 99.6 },
  { cameraId: "CAM-15", utilization: 85.3, uptime: 99.4 },
];

export const aiModelPerformance = {
  yoloVersion: "YOLOv9b",
  averageInference: "9.4ms",
  accuracy: 98.2,
  falsePositiveRate: 1.8,
  modelsLoaded: 4,
  gpuMemory: "3.2 GB / 8 GB",
  gpuTemp: 68,
};
