import http from "k6/http";
import { Counter } from "k6/metrics";
import { check, sleep } from "k6";

const allowedResponses = new Counter("allowed_responses");
const limitedResponses = new Counter("limited_responses");

export const options = {
  vus: 1,
  iterations: 5,
  thresholds: {
    checks: ["rate>0.99"],
    http_req_failed: ["rate<0.01"],
    allowed_responses: ["count>=1"],
    limited_responses: ["count>=1"],
  },
};

const url = "http://sample-api-service:8000/v1/echo";
const params = {
  headers: {
    "Content-Type": "application/json",
  },
};
const clientId = "load-test-client";

export default function () {
  const response = http.post(
    url,
    JSON.stringify({
      message: "hello from k6",
      client_id: clientId,
    }),
    params
  );

  if (response.status === 200) {
    allowedResponses.add(1);
  }

  if (response.status === 429) {
    limitedResponses.add(1);
  }

  check(response, {
    "status is 200 or 429": (r) => r.status === 200 || r.status === 429,
  });

  sleep(0.2);
}
