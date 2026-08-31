# Multi-stage build for the Quarkus backend.
#
# Stage 1 needs real Maven Central access to resolve Quarkus/Jakarta deps -
# this is NOT available in the sandbox this repo was developed in (see
# README's "Backend Java still isn't compiled here" note), but WILL work on
# any normal machine/CI runner with unrestricted internet access, since
# there's no special reason Maven Central would be blocked there.

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
# Cache dependency resolution as its own layer
RUN mvn -B dependency:go-offline || true
COPY src ./src
RUN mvn -B clean package -DskipTests

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=build /build/target/quarkus-app/lib/ ./lib/
COPY --from=build /build/target/quarkus-app/*.jar ./
COPY --from=build /build/target/quarkus-app/app/ ./app/
COPY --from=build /build/target/quarkus-app/quarkus/ ./quarkus/

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "quarkus-run.jar"]
