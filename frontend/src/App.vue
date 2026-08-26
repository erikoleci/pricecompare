<template>
  <v-app>
    <v-app-bar flat color="white" class="border-b">
      <v-container class="d-flex align-center">
        <router-link to="/" class="text-decoration-none d-flex align-center">
          <span class="text-h6 font-weight-bold text-primary">PriceCompare</span>
        </router-link>
        <v-spacer />
        <router-link to="/deals" class="mx-3 text-body-2 text-secondary text-decoration-none">Deals</router-link>
        <router-link to="/compare" class="mx-3 text-body-2 text-secondary text-decoration-none">Compare</router-link>
      </v-container>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
</script>
