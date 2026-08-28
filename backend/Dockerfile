# Multi-stage build: compile with Maven+JDK, run on a minimal JRE.
# NOTE: this could not be built/tested in the development sandbox used to
# write this project - the sandbox's network egress blocks repo.maven.apache.org
# (confirmed via a direct `mvn compile` attempt, see README's Phase 1
# "Live verification session" notes). Verify with a real `docker build` on a
# machine with normal internet access before deploying.

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
# cache dependencies in their own layer
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B clean package -DskipTests

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
RUN useradd -r -u 1001 -g root appuser
COPY --from=build /build/target/quarkus-app/lib/ ./lib/
COPY --from=build /build/target/quarkus-app/*.jar ./
COPY --from=build /build/target/quarkus-app/app/ ./app/
COPY --from=build /build/target/quarkus-app/quarkus/ ./quarkus/
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "quarkus-run.jar"]
