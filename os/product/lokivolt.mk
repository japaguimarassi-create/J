PRODUCT_PACKAGES += LokivoltSetup
PRODUCT_COPY_FILES += \
    vendor/lokivolt/config/identity-policy.json:$(TARGET_COPY_OUT_SYSTEM)/etc/lokivolt/identity-policy.json \
    vendor/lokivolt/config/reset-flow.json:$(TARGET_COPY_OUT_SYSTEM)/etc/lokivolt/reset-flow.json \
    vendor/lokivolt/config/fusion-architecture.json:$(TARGET_COPY_OUT_SYSTEM)/etc/lokivolt/fusion-architecture.json
