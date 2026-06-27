# Cloudflare R2 Storage Integration Documentation

This document explains how the Cloudflare R2 bucket (S3-compatible object storage) is integrated and utilized within the Hall Canteen project.

## Overview

The Hall Canteen backend uses Cloudflare R2 to store image uploads. Instead of saving large binary blobs or Base64-encoded images directly into the PostgreSQL database, the application uploads these files to the R2 bucket and stores only the resulting public URL in the database.

**Key Features:**
- **S3 Compatibility:** Interactions with the R2 bucket are handled using the `boto3` AWS SDK.
- **Base64 Processing:** The client sends images as Base64-encoded Data URLs. The backend decodes them, extracts the MIME type, and determines the correct file extension.
- **File Size Validation:** A configurable size limit (`upload_max_file_size_mb`) is enforced before uploading.
- **Unique Naming:** Files are renamed using UUIDs (`uuid.uuid4().hex`) to prevent naming collisions.
- **Async Execution:** The blocking `boto3` operations are executed asynchronously using FastAPI's `run_in_threadpool`.

## Supported Use Cases

Currently, the R2 storage is used in the following workflows:
1. **User Profile Updates:** Users can upload profile avatars. Images are saved with the `avatars/` prefix.
2. **Partner Onboarding:** Prospective partners must provide a photo of their shop when applying. These photos are saved with the `partner-applications/` prefix.

---

## 1. Use Case Diagram

The use case diagram illustrates the actors interacting with the system to trigger file uploads to the R2 bucket.

```mermaid
flowchart LR
    %% Actors
    Client((User / Partner\nClient))
    R2[(Cloudflare\nR2 Bucket)]

    %% System Boundary
    subgraph Backend [Hall Canteen Backend]
        UC1([Upload Avatar Image])
        UC2([Submit Partner Application Photo])
        UC3([Process Base64 Image Data])
        UC4([Store Object & Generate URL])
    end

    %% Relationships
    Client --> UC1
    Client --> UC2
    
    UC1 -.->|includes| UC3
    UC2 -.->|includes| UC3
    UC3 -.->|includes| UC4
    
    UC4 --> R2
```

---

## 2. Activity Diagram

The activity diagram shows the step-by-step logical flow of the `upload_data_url` function, which is the core utility for handling R2 uploads.

```mermaid
flowchart TD
    Start((Start)) --> A[Client submits Base64 Data URL]
    
    A --> B{Is URL already a valid\nHTTP/HTTPS link?}
    
    B -- Yes --> C[Return URL as-is\nIdempotent]
    C --> Stop1((Stop))
    
    B -- No --> D[Regex match Data URL]
    D --> E{Valid Data URL\nformat?}
    
    E -- No --> F[Throw StorageError\n400 - Invalid Format]
    F --> Stop2((Stop))
    
    E -- Yes --> G[Extract MIME type & Extension]
    G --> H[Decode Base64 to Bytes]
    H --> I{Decode successful\n& not empty?}
    
    I -- No --> J[Throw StorageError\n400 - Invalid Base64/Empty]
    J --> Stop3((Stop))
    
    I -- Yes --> K[Check Byte Size]
    K --> L{Size <= Max\nAllowed Size?}
    
    L -- No --> M[Throw StorageError\n400 - File Too Large]
    M --> Stop4((Stop))
    
    L -- Yes --> N[Generate unique Key\nPrefix + UUID + Ext]
    N --> O[boto3 client put_object to R2]
    O --> P{Upload\nsuccessful?}
    
    P -- No --> Q[Throw StorageUploadError\n502]
    Q --> Stop5((Stop))
    
    P -- Yes --> R[Construct Public URL]
    R --> S[Return Public URL]
    S --> Stop6((Stop))
```

---

## 3. Sequence Diagram

The sequence diagram demonstrates the communication between the Client, the FastAPI Backend Service, and the Cloudflare R2 bucket during an image upload process (e.g., uploading an avatar).

```mermaid
sequenceDiagram
    participant C as Client (Frontend)
    participant API as FastAPI Backend (auth.py / partner.py)
    participant Storage as Storage Core (storage.py)
    participant R2 as Cloudflare R2
    participant DB as PostgreSQL Database

    C->>API: PUT /profile (Base64 avatar image)
    API->>Storage: upload_data_url(data_url, prefix="avatars")
    
    alt is already an HTTP URL
        Storage-->>API: return existing URL
    else is Base64 Data URL
        Storage->>Storage: _decode_data_url(data_url)
        Storage->>Storage: validate size limits
        Storage->>Storage: generate unique file key
        
        Storage->>R2: put_object(Bucket, Key, Body, ContentType)
        
        alt Upload Success
            R2-->>Storage: HTTP 200 OK
            Storage-->>API: return public URL (r2_public_url + key)
        else Upload Failed
            R2-->>Storage: BotoCoreError / ClientError
            Storage-->>API: raise StorageUploadError
            API-->>C: 502 Bad Gateway
        end
    end

    API->>DB: update User avatar URL
    DB-->>API: success
    API-->>C: 200 OK (Profile updated)
```

## Environment Configuration

The R2 storage relies on the following environment variables defined in `config.py`:

- `R2_ENDPOINT`: The S3 API endpoint provided by Cloudflare.
- `R2_ACCESS_KEY_ID`: Cloudflare R2 Access Key.
- `R2_SECRET_ACCESS_KEY`: Cloudflare R2 Secret Key.
- `R2_BUCKET`: The name of the bucket (e.g., `hall-canteen-assets`).
- `R2_PUBLIC_URL`: The custom domain or `r2.dev` public URL mapped to the bucket.
- `UPLOAD_MAX_FILE_SIZE_MB`: The maximum allowed file size in megabytes (default is 10 MB).
