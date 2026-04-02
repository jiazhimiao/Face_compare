# Java Integration Contract

## Service Positioning

This Python service is the algorithm side only. It should not take over business-domain responsibilities already owned by Java.

### Java responsibilities

1. Receive external business requests.
2. Handle authentication, authorization, order orchestration, and workflow composition.
3. Call the Python face-comparison service.
4. Persist business records.
5. Handle audit, alerts, and platform-level monitoring.

### Python responsibilities

1. Face detection
2. Identity verification
3. Blacklist matching
4. Feature caching
5. Model inference

## Recommended Calling Pattern

```text
Client
-> Java backend
-> Python face service
-> Java backend persistence / audit / response assembly
```

## Authentication

Header:

```text
X-API-Token: <token>
```

Optional request trace header:

```text
X-Request-Id: <uuid-or-order-id>
```

## API Endpoints

### 1. Liveness

`GET /api/v1/health/live`

### 2. Readiness

`GET /api/v1/health/ready`

### 3. Face Detection

`POST /api/v1/detect-face`

Multipart fields:

- `image`

### 4. Identity Verification

`POST /api/v1/verify-identity`

Multipart fields:

- `id_card_image`
- `face_image`

### 5. Blacklist Check

`POST /api/v1/check-blacklist`

Multipart fields:

- `image`

## Standard Response Envelope

Success:

```json
{
  "success": true,
  "request_id": "trace-id",
  "message": "OK",
  "error_code": null,
  "data": {}
}
```

Failure:

```json
{
  "success": false,
  "request_id": "trace-id",
  "message": "Missing or invalid API token",
  "error_code": "AUTH_401",
  "data": {},
  "details": {}
}
```

## Error Code Suggestions

- `AUTH_401`: invalid token
- `REQ_400`: request field missing or invalid
- `FILE_413`: file too large
- `FILE_415`: unsupported image type
- `FACE_404`: face not found in required image
- `SVC_500`: internal unexpected failure
- `SVC_503`: dependency or model/cache unavailable

## Java-side Integration Notes

1. Java should treat Python responses as algorithm results, not final business decisions.
2. Java should persist original order id, request id, and algorithm result summary.
3. Java should set a request timeout and fallback policy.
4. Java should keep the API token in a secure config center, not in code.
5. Java should own downstream auditing and alarming, even though the Python service writes local runtime logs.

## Java Request Examples

### cURL example

```bash
curl -X POST "http://127.0.0.1:5000/api/v1/verify-identity" \
  -H "X-API-Token: replace-with-secure-token" \
  -H "X-Request-Id: order-20260401-001" \
  -F "id_card_image=@/path/to/id_card.jpeg" \
  -F "face_image=@/path/to/face_photo.jpeg"
```

### Spring Boot `RestTemplate` example

```java
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.io.File;
import java.util.Map;

public class FaceCompareClient {

    private final RestTemplate restTemplate = new RestTemplate();
    private final String baseUrl = "http://127.0.0.1:5000";
    private final String apiToken = "replace-with-secure-token";

    public Map verifyIdentity(File idCardImage, File faceImage, String requestId) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        headers.add("X-API-Token", apiToken);
        headers.add("X-Request-Id", requestId);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("id_card_image", new FileSystemResource(idCardImage));
        body.add("face_image", new FileSystemResource(faceImage));

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        ResponseEntity<Map> response = restTemplate.exchange(
            baseUrl + "/api/v1/verify-identity",
            HttpMethod.POST,
            requestEntity,
            Map.class
        );

        return response.getBody();
    }
}
```

### Spring Boot `WebClient` example

```java
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.File;
import java.util.Map;

public class FaceCompareWebClient {

    private final WebClient webClient = WebClient.builder()
        .baseUrl("http://127.0.0.1:5000")
        .defaultHeader("X-API-Token", "replace-with-secure-token")
        .build();

    public Map<String, Object> checkBlacklist(File imageFile, String requestId) {
        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        builder.part("image", new FileSystemResource(imageFile));

        return webClient.post()
            .uri("/api/v1/check-blacklist")
            .header("X-Request-Id", requestId)
            .contentType(MediaType.MULTIPART_FORM_DATA)
            .bodyValue(builder.build())
            .retrieve()
            .bodyToMono(Map.class)
            .block();
    }
}
```

## Suggested Java DTO Shape

```java
public class FaceServiceResponse<T> {
    private boolean success;
    private String requestId;
    private String message;
    private String errorCode;
    private T data;
}
```

Identity verification payload example:

```java
public class IdentityVerificationData {
    private String idCardPath;
    private String faceImagePath;
    private IdentityVerificationResult identityVerification;
}

public class IdentityVerificationResult {
    private boolean verified;
    private double similarity;
    private double threshold;
    private String message;
    private int idCardFaceCount;
    private int faceImageFaceCount;
    private List<Integer> idCardBbox;
    private List<Integer> faceBbox;
}
```

## Java-side Timeout And Fallback

Recommended baseline:

1. Java HTTP client timeout: `10s` to `15s` on CPU deployment.
2. If Python returns `SVC_504`, Java should mark the algorithm call as timeout and decide whether to retry.
3. If Python returns `FACE_404`, Java should convert that into a business-friendly message such as "未检测到有效人脸".
4. Java should not rely on local file paths returned by Python as long-term storage identifiers.

## Suggested Java-side Service Boundary

Inside Java, keep a dedicated client component:

```text
FaceCompareGateway
-> callDetectFace()
-> callVerifyIdentity()
-> callCheckBlacklist()
```

That gateway should be the only module that knows:

- Python base URL
- API token
- request timeout
- response parsing
- retry policy
