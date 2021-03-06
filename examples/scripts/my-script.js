client.test("Request executed successfully", function() {
    client.assert(response.status === 410, "Response status is not 410");
});

client.test("Headers option exists", function() {
    client.assert(response.body.hasOwnProperty("headers"), "Cannot find 'headers' option in response");
});

client.test("Response content-type is json", function() {
    var type = response.contentType.mimeType;
    client.assert(type === "application/json", "Expected 'application/json' but received '" + type + "'");
});
