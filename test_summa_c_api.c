#include <stdio.h>

extern void _gfortran_set_args(int argc, char **argv);

extern void summa_evaluate(double *param_values, int n, double *objective, int *err);

int main(int argc, char **argv) {
    _gfortran_set_args(argc, argv);

    double params[3] = {7.5e-06, 0.55, 1.3};
    int n = 3;
    double objective = 0.0;
    int err = -1;

    printf("Calling summa_evaluate with params: k_soil=%.3e, theta_sat=%.3f, vGn_n=%.3f\n",
           params[0], params[1], params[2]);

    summa_evaluate(params, n, &objective, &err);

    printf("err       = %d\n", err);
    printf("objective = %.10f\n", objective);

    return err;
}
