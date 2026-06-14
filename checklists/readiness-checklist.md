# Readiness Checklist — A7 Notification Service (Lab 05)

| # | Tiêu chí | Trạng thái |
|---|----------|------------|
| 1 | DB đã khởi động và sẵn sàng (`pg_isready`) | ✅ |
| 2 | AI service có health check trả 200 | ✅ |
| 3 | API kết nối được và `/health` trả 200 | ✅ |
| 4 | Biến môi trường đặt đúng, không dùng secret thật | ✅ |
| 5 | `team-internal` network hoạt động, service gọi nội bộ được | ✅ |
| 6 | Version/tag image đúng quy ước (`notify:1.0.0`) | ✅ |

## Readiness chi tiết

- **Healthcheck**: `depends_on` + `condition: service_healthy` đảm bảo DB và AI sẵn sàng trước khi API start
- **Env Validation**: Biến môi trường khai báo trong `.env.example`, không commit secret thật
- **Graceful Shutdown**: `docker compose down` dừng container sạch
- **Error Handling**: Request lỗi trả về ProblemDetails (401, 422)
- **Auth**: Endpoint `/api/notifications` yêu cầu Bearer token
- **Newman Test**: 11 requests, 24 assertions, 0 failed